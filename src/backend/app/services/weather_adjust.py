"""Exogenous weather consumption for forecasting — W2 reads W1's pipeline output.

The weather pipeline (app.pipelines.weather) owns ingestion; this module owns
how a forecast consumes the stored series: loading the horizon window, scoring
adverse-weather severity, and applying the adjustment to a ForecastResult.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from ..config import get_settings
from ..models import WeatherObservation

HORIZON = 72

MIN_WEATHER_ROWS = 2          # fewer usable weather hours than this -> treat weather as unavailable
# (audit-fix: the pipeline stores the current hour plus forecast hours; 6 made the
# weather_used flag unreachable on live data — a 72h refresh yields ~73 usable rows now)
WEATHER_INDEX_LIFT = 12.0     # max index points added by the most severe forecast weather
WEATHER_BAND_LIFT = 10.0      # max extra half-band width (index points) under adverse weather


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def load_weather_series(db, t0: datetime | None = None, horizon: int = HORIZON) -> list[dict]:
    """W2 consumes W1's weather (WeatherObservation) — the pipeline itself stays W1's.

    Returns forecast-horizon points (``hours_ago`` <= 0) keyed by hours ahead. Never
    raises: an empty list means "weather unavailable" and forecasting still works.
    """
    if db is None:
        return []
    try:
        rows = db.execute(
            select(WeatherObservation)
            .where(WeatherObservation.hours_ago <= 0)
            .where(WeatherObservation.hours_ago >= -horizon)
            .order_by(WeatherObservation.hours_ago.desc())
        ).scalars().all()
    except Exception:  # noqa: BLE001 - weather must never break forecasting
        return []
    return [{
        "hours_ahead": max(1, -int(r.hours_ago)),
        "hours_ago": int(r.hours_ago),
        "wind_kn": r.wind_kn,
        "gust_kn": r.gust_kn,
        "wave_m": r.wave_m,
        "visibility_km": r.visibility_km,
    } for r in rows]


def weather_severity(w: dict) -> float:
    """0..1 adverse-weather severity from the frozen schema (gust/wind, wave, visibility)."""
    gust = w.get("gust_kn") if w.get("gust_kn") is not None else w.get("wind_kn")
    wave = w.get("wave_m")
    vis = w.get("visibility_km")
    sev = 0.0
    if gust is not None:
        sev += 0.6 * clip((float(gust) - 25.0) / 25.0, 0.0, 1.0)
    if wave is not None:
        sev += 0.3 * clip((float(wave) - 2.5) / 2.5, 0.0, 1.0)
    if vis is not None:
        sev += 0.1 * clip((5.0 - float(vis)) / 5.0, 0.0, 1.0)
    return clip(sev, 0.0, 1.0)


def apply_weather_adjustment(fc, weather: list[dict]) -> bool:
    """Exogenous weather adjustment — W2 consumes W1 weather, it never rebuilds the pipeline.

    Applied only when ``FEATURE_WEATHER`` is on and >= MIN_WEATHER_ROWS usable weather hours
    exist. Raises the index/queue/wait under adverse conditions, widens the bands and flips
    ``weather_used``. Returns True iff weather was actually used.
    """
    settings = get_settings()
    if not settings.feature_weather or fc.weather_used or not weather:
        return False
    by_ahead = {int(w["hours_ahead"]): w for w in weather if w.get("hours_ahead")}
    if len(by_ahead) < MIN_WEATHER_ROWS:
        return False
    sev = {h: weather_severity(w) for h, w in by_ahead.items()}
    max_sev = max(sev.values(), default=0.0)
    if max_sev <= 0.0:
        return False
    nearest = sorted(by_ahead)
    for p in fc.points:
        s = sev.get(p.hour)
        if s is None:
            near = min(nearest, key=lambda h: abs(h - p.hour))
            s = sev.get(near, 0.0)
        if s <= 0:
            continue
        p.index = round(clip(p.index + WEATHER_INDEX_LIFT * s, 0.0, 100.0), 1)
        p.queue = round(p.queue * (1.0 + 0.15 * s), 1)
        p.wait = round(p.wait * (1.0 + 0.20 * s), 1)
        extra = WEATHER_BAND_LIFT * s
        p.lo = round(max(0.0, p.lo - extra), 1)
        p.hi = round(min(100.0, p.hi + extra), 1)
        # widen the per-target intervals too
        p.queue_lo = round(max(0.0, p.queue_lo - 0.3 * extra), 1)
        p.queue_hi = round(p.queue_hi + 0.3 * extra, 1)
        p.wait_lo = round(max(1.0, p.wait_lo - 0.5 * extra), 1)
        p.wait_hi = round(p.wait_hi + 0.5 * extra, 1)
        p.yard_lo = round(max(0.0, p.yard_lo - 0.3 * extra), 1)
        p.yard_hi = round(min(100.0, p.yard_hi + 0.3 * extra), 1)
    peak = max(fc.points, key=lambda p: p.index)
    fc.peak = {"hour": peak.hour, "index": peak.index}
    fc.avg_index = round(sum(p.index for p in fc.points) / len(fc.points), 1)
    fc.drivers = list(fc.drivers) + [{
        "label": "Adverse weather",
        "detail": f"Weather signal applied (peak severity {max_sev:.2f}) to index/queue/wait; bands widened."}]
    fc.weather_used = True
    if getattr(fc, "horizons", None):
        from .forecasting import _horizon_summary  # local import: avoids a cycle at module load
        fc.horizons = _horizon_summary(fc.points)
    if isinstance(fc.model, dict):
        fc.model["weather_used"] = True
    return True
