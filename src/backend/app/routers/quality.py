"""Data-quality + weather capability (W1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Terminal, WeatherObservation
from ..response_models import QualityResponse, WeatherResponse

router = APIRouter(prefix="/api", tags=["quality"])


def run_normalisation_pass(db: Session) -> int:
    """Normalise columns + recompute terminal completeness (the write side of Module D).

    Invoked explicitly: at startup (main.py lifespan) and via POST /api/quality/refresh —
    never as a side effect of a GET. Schema v2: ft→m, hours→seconds, UTC timestamps.
    Audit B-9: vessels are attributed via ``Terminal.zone_code == dest_zone_code``.
    """
    from ..services.dataquality import NormalisationEngine, compute_terminal_quality

    normalised_count = NormalisationEngine(db).run()
    compute_terminal_quality(db)
    return normalised_count


@router.post("/quality/refresh")
def quality_refresh(db: Session = Depends(get_db)):
    """Explicit normalisation + completeness recompute (the write side of Module D)."""
    normalised_count = run_normalisation_pass(db)
    return {"status": "ok", "normalised_rows_updated": normalised_count}


@router.get("/quality", response_model=QualityResponse)
def quality(db: Session = Depends(get_db)):
    """Read the last computed per-terminal data-completeness snapshot (Module D).

    Read-only by design (spec: GETs must be idempotent; B-5): normalisation runs
    explicitly at startup or via POST /api/quality/refresh, never on this path.
    """
    from ..models import TerminalQuality
    from sqlalchemy import func

    stmt = select(Terminal.code, Terminal.name, TerminalQuality.completeness_pct,
                  TerminalQuality.missing, TerminalQuality.rules_version).join(
        TerminalQuality, Terminal.id == TerminalQuality.terminal_id)
    rows = db.execute(stmt).all()
    terminals = [{"terminal_code": code, "name": name, "completeness_pct": pct,
                  "missing": missing or [], "rules_version": version or "v2"}
                 for code, name, pct, missing, version in rows]
    rules_version = rows[0][4] if rows else "v2"
    # Freshness of the persisted snapshot (when the last explicit pass ran), served
    # read-only so the UI can flag staleness — never a write-on-read.
    last_run_at = db.execute(select(func.max(TerminalQuality.observed_at))).scalar()
    return {"terminals": terminals, "rules_version": rules_version,
            "last_run_at": last_run_at.isoformat() if last_run_at else None, "stub": False}


@router.post("/weather/refresh")
def weather_refresh(db: Session = Depends(get_db), hours: int = Query(72, ge=24, le=336)):
    """Run the W1 Open-Meteo pipeline and persist `WeatherObservation` rows.

    Audit B-6: the pipeline existed but was never invoked, so `FEATURE_WEATHER` was
    unreachable and `weather_used` stayed false forever. This is the missing wiring.
    If Open-Meteo is unreachable the pipeline inserts nothing and this returns an
    empty series — the forecast then reports `weather_used: false` instead of failing.
    """
    from ..pipelines.weather import run_weather_pipeline

    run_weather_pipeline(db, hours=hours)
    return _weather_points(db, hours)


@router.get("/weather", response_model=WeatherResponse)
def weather(db: Session = Depends(get_db), hours: int = Query(72, ge=1, le=336)):
    """Wind/wave/visibility series for San Pedro Bay (rows persisted by the pipeline)."""
    return _weather_points(db, hours)


def _weather_points(db: Session, hours: int) -> dict:

    stmt = select(WeatherObservation).where(
        WeatherObservation.hours_ago <= 0,
        WeatherObservation.hours_ago >= -hours,
    ).order_by(WeatherObservation.hours_ago)
    obs = db.execute(stmt).scalars().all()
    points = [{
        "hour": o.hours_ago, "ts": o.ts.isoformat(), "wind_kn": o.wind_kn,
        "gust_kn": o.gust_kn, "wave_m": o.wave_m, "visibility_km": o.visibility_km,
    } for o in obs]
    return {"points": points, "source": "OPEN_METEO", "hours": hours, "stub": False}


@router.post("/bts/parse")
def bts_parse(file: UploadFile = File(...)):
    """Audit B-7: wire the BTS PPFSP benchmark parser to an endpoint (was dead code).

    Accepts a BTS weekly-berthing CSV, validates and parses it, returning the rows
    for forecast validation. Keeps the benchmark load-bearing.
    """
    from ..pipelines.bts import run_bts_pipeline

    raw = file.file.read()
    return run_bts_pipeline(raw)
