"""Optimisation capability: OR-Tools CP-SAT BAP/QCAP runs (W3).

Scenario endpoints live in routers/scenarios.py (moved in Phase 0).
FROZEN SHAPE for POST /api/optimise: existing keys + `tidal_feasible`, `incremental`.

Both switches accept **either** a JSON body field or a query param, so the documented
`POST /api/optimise?incremental=1` form works as well as `{"incremental": true}`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Assignment, Berth, OptimiserRun, TidalWindow, VesselCall
from ..response_models import OptimiseLatest, TidesResponse
from ..services import pipeline, tides

router = APIRouter(prefix="/api", tags=["optimise"])


class ScenarioBody(BaseModel):
    crane_factor: float = Field(1.0, ge=0.5, le=1.0, description="crane availability multiplier")
    move_rate_per_crane_hour: float = Field(28.0, ge=20.0, le=35.0)
    # Tri-state on purpose (W3): None means "not specified → fall back to the feature flag",
    # while an explicit false must be able to switch the feature OFF from the UI. A plain
    # `bool = False` default cannot express that distinction once FEATURE_* defaults to true.
    incremental: bool | None = Field(None, description="warm-start from the previous CP-SAT solution (W3)")
    tidal: bool | None = Field(None, description="enforce tidal windows on deep-draft vessels (W3)")


def _resolve(query_val: bool | None, body_val: bool | None, flag: bool) -> bool:
    """Most specific wins: query param → JSON body → feature-flag default."""
    if query_val is not None:
        return bool(query_val)
    if body_val is not None:
        return bool(body_val)
    return bool(flag)


@router.get("/optimise/latest", response_model=OptimiseLatest)
def latest(db: Session = Depends(get_db)):
    run = db.execute(select(OptimiserRun).order_by(OptimiserRun.id.desc())).scalars().first()
    if run is None:
        return pipeline.build_full(db, persist=False)["optimiser"]
    rows = db.execute(select(Assignment).where(Assignment.run_id == run.id).order_by(Assignment.sequence)).scalars().all()
    berths = {b.id: b for b in db.execute(select(Berth)).scalars().all()}
    vessels = {v.id: v for v in db.execute(select(VesselCall)).scalars().all()}
    assignments = []
    for a in rows:
        b, v = berths[a.berth_id], vessels[a.vessel_call_id]
        assignments.append({"vessel_id": v.id, "vessel_name": v.name, "carrier": v.carrier,
                            "vessel_class": v.vessel_class, "berth_id": b.id, "berth_name": b.name,
                            "terminal_id": b.terminal_id, "start_hour": a.start_hour,
                            "end_hour": a.end_hour, "cranes": a.cranes, "wait_hours": a.wait_hours,
                            "priority_score": a.priority_score})
    p = run.params or {}
    return {"run_id": run.id, "solver": run.solver, "status": run.status, "objective": run.objective,
            "solve_ms": run.solve_ms, "assignments": assignments, "metrics": run.metrics,
            "baseline": run.baseline, "deltas": run.deltas, "deferred": run.deferred, "weights": run.weights,
            "tidal_feasible": p.get("tidal_feasible", True), "incremental": bool(p.get("incremental")),
            "gap_pct": p.get("gap_pct")}


@router.post("/optimise", response_model=OptimiseLatest)
def run_optimise(body: ScenarioBody,
                 incremental: bool | None = Query(None, description="alias for body.incremental (W3)"),
                 tidal: bool | None = Query(None, description="alias for body.tidal (W3)"),
                 db: Session = Depends(get_db)):
    # query param OR body field OR feature flag. The flags are read here, at the API edge,
    # so the engine stays deterministic for unit tests that call optimiser.optimise() directly.
    settings = get_settings()
    use_incremental = _resolve(incremental, body.incremental, settings.feature_incremental)
    use_tidal = _resolve(tidal, body.tidal, settings.feature_tidal)
    if use_tidal:
        # keep the frozen TidalWindow table load-bearing: materialise the modelled
        # curve once (idempotent no-op when W1 has already seeded real soundings)
        tides.ensure_windows(db)
    scenario = {"crane_factor": body.crane_factor, "move_rate_per_crane_hour": body.move_rate_per_crane_hour,
                "incremental": use_incremental, "tidal": use_tidal}
    return pipeline.build_full(db, scenario=scenario, persist=True)["optimiser"]


@router.get("/tides", response_model=TidesResponse)
def get_tides(hours: int = Query(72, ge=24, le=168), db: Session = Depends(get_db)):
    """W3: tidal depth curve for every berth (read-only).

    Serves whatever the tide pipeline last persisted — NOAA CO-OPS rows when present,
    else the labelled harmonic model — as depth_ft at each integer hour 0..hours per
    berth. A GET never fetches or writes: the write side lives at startup (main.py)
    and POST /api/tides/refresh.
    """
    has_noaa = db.execute(
        select(TidalWindow.id).where(TidalWindow.note == tides.NOAA_NOTE).limit(1)
    ).first() is not None
    source = tides.NOAA_NOTE if has_noaa else tides.HARMONIC_NOTE
    berths = db.execute(select(Berth)).scalars().all()
    return {
        "period_hours": tides.TIDE_PERIOD_H,
        "amplitude_ft": tides.TIDE_AMPLITUDE_FT,
        "under_keel_margin_ft": get_settings().under_keel_margin_ft,
        "source": source,
        "berths": [
            {
                "berth_id": b.id,
                "berth_name": b.name,
                "design_depth_ft": b.depth_ft,
                "curve": tides.snapshot(b.id, b.depth_ft, hours),
            }
            for b in berths
        ],
    }


@router.post("/tides/refresh")
def refresh_tides(hours: int = Query(96, ge=24, le=168), db: Session = Depends(get_db)):
    """Force a fresh NOAA CO-OPS fetch and replace tidal window rows.

    Returns {source, rows_written, station} — callable from the QualityPage refresh button.
    """
    noaa_written = tides.fetch_noaa_tides(db, horizon_hours=hours)
    if noaa_written == 0:
        # NOAA unavailable — refresh harmonic model
        tides.ensure_windows(db, horizon_hours=hours, force=True)
    return {
        "source": tides.NOAA_NOTE if noaa_written > 0 else tides.HARMONIC_NOTE,
        "rows_written": noaa_written if noaa_written > 0 else None,
        "station": tides.NOAA_STATION_ID,
        "hours": hours,
    }
