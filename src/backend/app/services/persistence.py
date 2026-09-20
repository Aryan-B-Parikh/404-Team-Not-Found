"""Persistence for engine-run results (the write side of the pipeline).

Split from the former god-assembler ``pipeline.py`` so compute and persistence are
separable: ``run_*`` functions orchestrate engines, ``persist_*`` functions own the
writes. Every function here takes an explicit ``db`` — no hidden session state.
"""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (AnomalyFlag, Assignment, ForecastPoint, ForecastRun, OperationsPlan,
                      OptimiserRun, RoutingRecommendation)
from . import forecasting as fc_svc
from . import llm as llm_svc
from .context import EngineContext


def persist_forecast_run(db: Session, forecasts: dict, ctx: EngineContext) -> int:
    port = forecasts["Z-PORT"]
    run = ForecastRun(model_version=port.model["model_version"], algorithm=port.model.get("algorithm", "LightGBM"),
                      horizon_hours=fc_svc.HORIZON,
                      metrics={z: {k: f.model.get(k) for k in ("mae24", "mae72", "r2", "skill_pct", "training_rows")} for z, f in forecasts.items()},
                      data_version=ctx.data_version,
                      feature_flags={"weather": bool(get_settings().feature_weather),
                                     "weather_used": bool(getattr(port, "weather_used", False)),
                                     "dataset_source": ctx.dataset_source})
    db.add(run); db.flush()
    for z, fc in forecasts.items():
        for p in fc.points:
            db.add(ForecastPoint(run_id=run.id, zone_code=z, hour=p.hour, ts=p.ts, index=p.index,
                                 queue=p.queue, wait=p.wait, yard_util_pct=p.yard_util, lo=p.lo, hi=p.hi))
    db.commit(); return run.id


def persist_anomalies(db: Session, flags: list[dict]) -> None:
    db.execute(delete(AnomalyFlag))
    for f in flags:
        db.add(AnomalyFlag(zone_code=f["zone_code"], kind=f["kind"], method=f["method"], score=f["score"], is_anomaly=f["is_anomaly"], sample_size=f["sample_size"], detail=f["detail"], features=f["features"]))
    db.commit()


def persist_optimiser_run(db: Session, out: dict) -> int:
    run = OptimiserRun(solver=out["solver"], status=out["status"], objective=out["objective"], solve_ms=out["solve_ms"], params=out["params"], metrics=out["metrics"], baseline=out["baseline"], deltas=out["deltas"], deferred=out["deferred"], weights=out["weights"])
    db.add(run); db.flush()
    for i, a in enumerate(out["assignments"]):
        db.add(Assignment(run_id=run.id, vessel_call_id=a["vessel_id"], berth_id=a["berth_id"], start_hour=a["start_hour"], end_hour=a["end_hour"], cranes=a["cranes"], wait_hours=a["wait_hours"], priority_score=a["priority_score"], sequence=i))
    db.commit(); return run.id


def persist_routing(db: Session, recs: list[dict]) -> None:
    db.execute(delete(RoutingRecommendation))
    for r in recs:
        db.add(RoutingRecommendation(vessel_call_id=r["vessel_id"], option=r["option"], target_port=r.get("target_port"), eta_shift_hours=r.get("eta_shift_hours", 0), predicted_wait_hours=r["predicted_wait_hours"], est_savings_usd=r["est_savings_usd"], confidence=r["confidence"], tier=r["tier"], rationale=r.get("rationale"), sustained=bool(r.get("sustained")), option_detail=r.get("option_detail")))
    db.commit()


def persist_plan(db: Session, plan_out: dict) -> int:
    narrative, source = llm_svc.narrate(plan_out["text"], plan_out["summary"])
    row = OperationsPlan(horizon_hours=72, forecast_run_id=plan_out["summary"].get("forecast_run_id"), optimiser_run_id=plan_out["summary"].get("optimiser_run_id"), summary=plan_out["summary"], shifts=plan_out["shifts"], text_plan=plan_out["text"], narrative_source=source)
    db.add(row); db.commit(); plan_out["narrative"] = narrative; plan_out["narrative_source"] = source; return row.id
