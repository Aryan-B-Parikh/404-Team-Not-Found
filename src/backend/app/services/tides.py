"""Tidal windows with NOAA CO-OPS predictions and labelled harmonic fallback."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import httpx
from sqlalchemy import select

from ..config import get_settings

LOGGER = logging.getLogger(__name__)
TIDE_PERIOD_H = 12.42
TIDE_AMPLITUDE_FT = 2.8
HARMONIC_NOTE = "harmonic-model"
NOAA_NOTE = "noaa-coops"
NOAA_STATION_ID = "9410660"
NOAA_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NOAA_PRODUCT_PREDICTIONS = "predictions"
NOAA_DATUM = "MLLW"
NOAA_UNITS = "english"
NOAA_TIME_ZONE = "GMT"


def _phase_hours(berth_id: int) -> float: return (berth_id % 12) * 0.5

def depth_ft(design_depth_ft: float, hour: float, berth_id: int = 0) -> float:
    return design_depth_ft + TIDE_AMPLITUDE_FT * math.cos(2 * math.pi * (hour - _phase_hours(berth_id)) / TIDE_PERIOD_H)


def _ukc() -> float: return max(0.0, get_settings().under_keel_margin_ft)

def needs_tide(design_depth_ft: float, draft_ft: float) -> bool: return draft_ft + _ukc() > design_depth_ft


@lru_cache(maxsize=1)
def _db_overrides() -> dict[int, dict[int, float]]:
    try:
        from ..db import SessionLocal
        from ..models import TidalWindow
        db = SessionLocal()
        try:
            out = {}
            for row in db.execute(select(TidalWindow)).scalars().all(): out.setdefault(row.berth_id, {})[row.hours_ago] = row.min_depth_ft
            return out
        finally: db.close()
    except Exception as exc:
        LOGGER.warning("no persisted tide windows (%s); harmonic model only", exc)
        return {}


def invalidate_cache() -> None: _db_overrides.cache_clear()


def fetch_noaa_tides(db, horizon_hours: int = 96, t0: datetime | None = None) -> int:
    from ..models import Berth, TidalWindow
    base_ts = (t0 or datetime.now(timezone.utc)).replace(minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    end_ts = base_ts + timedelta(hours=horizon_hours)
    try:
        resp = httpx.get(NOAA_API_BASE, params={"station": NOAA_STATION_ID, "product": NOAA_PRODUCT_PREDICTIONS,
            "begin_date": base_ts.strftime("%Y%m%d %H:%M"), "end_date": end_ts.strftime("%Y%m%d %H:%M"),
            "datum": NOAA_DATUM, "time_zone": NOAA_TIME_ZONE, "interval": "h", "units": NOAA_UNITS,
            "application": "PortPulseAI", "format": "json"}, timeout=15)
        resp.raise_for_status(); data = resp.json()
    except Exception as exc:
        LOGGER.warning("NOAA CO-OPS fetch failed; harmonic fallback remains active: %s", exc); return 0
    predictions = data.get("predictions", []); wl = {}
    for p in predictions:
        try:
            ts = datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            hour = int(round((ts - base_ts).total_seconds() / 3600)); wl[hour] = float(p["v"])
        except (KeyError, ValueError, TypeError): continue
    if not wl: return 0
    berths = db.execute(select(Berth)).scalars().all()
    from sqlalchemy import delete
    # NOAA rows cover the same (berth_id, hours_ago) keys as any persisted harmonic
    # rows, and uq_tide_berth_hours would reject them — clear the covered range first
    # or the fetch can never actually persist once the fallback has run.
    db.execute(delete(TidalWindow).where(TidalWindow.hours_ago <= horizon_hours))
    written = 0
    for b in berths:
        for hour, level in wl.items():
            db.add(TidalWindow(berth_id=b.id, ts=base_ts + timedelta(hours=hour), hours_ago=hour,
                               min_depth_ft=round(b.depth_ft + level, 3), note=NOAA_NOTE)); written += 1
    try:
        db.commit(); invalidate_cache()
    except Exception as exc:
        db.rollback(); LOGGER.warning("NOAA tide persistence failed: %s", exc); return 0
    return written


def ensure_windows(db, horizon_hours: int = 96, t0: datetime | None = None, force: bool = False) -> int:
    from ..models import Berth, TidalWindow
    if db.execute(select(TidalWindow.id).limit(1)).first() is not None and not force: return 0
    if force: db.query(TidalWindow).delete()
    base_ts = (t0 or datetime.now(timezone.utc)).astimezone(timezone.utc); berths = db.execute(select(Berth)).scalars().all(); written = 0
    for b in berths:
        for hour in range(horizon_hours + 1):
            db.add(TidalWindow(berth_id=b.id, ts=base_ts + timedelta(hours=hour), hours_ago=hour,
                               min_depth_ft=round(depth_ft(b.depth_ft, hour, b.id), 3), note=HARMONIC_NOTE)); written += 1
    db.commit(); invalidate_cache(); return written


def depth_at(berth_id: int, design_depth_ft: float, hour: int) -> float:
    over = _db_overrides().get(berth_id)
    return over[hour] if over and hour in over else depth_ft(design_depth_ft, hour, berth_id)


def is_open(berth_id: int, design_depth_ft: float, draft_ft: float, hour: int) -> bool:
    return depth_at(berth_id, design_depth_ft, hour) >= draft_ft + _ukc()


def allowed_start_hours(berth_id: int, design_depth_ft: float, draft_ft: float, horizon_hours: int) -> list[int]:
    return [h for h in range(horizon_hours + 1) if is_open(berth_id, design_depth_ft, draft_ft, h)]


def snapshot(berth_id: int, design_depth_ft: float, horizon_hours: int) -> list[dict]:
    """Return [{hour, depth_ft}] for hours 0..horizon_hours inclusive (used by the tides UI curve)."""
    return [{"hour": h, "depth_ft": round(depth_at(berth_id, design_depth_ft, h), 3)}
            for h in range(horizon_hours + 1)]
