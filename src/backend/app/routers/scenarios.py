"""Scenario / what-if capability (W3).

Every extended scenario now runs the full forecast + hotspot + optimisation
pipeline against the modified in-memory context. This keeps vessel bunching and
schedule changes causally connected to forecast outputs instead of reusing the
baseline forecast.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ImpactAssessment, Scenario
from ..response_models import ScenarioExtendedResponse, ScenarioResponse, ScenarioRollbackResponse
from ..services import pipeline, scenarios as scen_svc
from ..services.context import EngineContext

router = APIRouter(prefix="/api", tags=["scenarios"])


class ScenarioBody(BaseModel):
    crane_factor: float = Field(1.0, ge=0.5, le=1.0)
    move_rate_per_crane_hour: float = Field(28.0, ge=20.0, le=35.0)


class ExtendedScenarioBody(BaseModel):
    """W3: berth add/remove, crane outage, vessel bunching, schedule change."""
    kind: str = Field("CRANE_OUTAGE", description="CRANE_OUTAGE | PRODUCTIVITY | BERTH_REMOVED | BERTH_ADDED | BUNCHING | SCHEDULE_CHANGE")
    crane_factor: float = Field(1.0, ge=0.5, le=1.0)
    move_rate_per_crane_hour: float = Field(28.0, ge=20.0, le=35.0)
    terminal_code: str | None = None
    berth_count_delta: int = Field(0, ge=0, le=8)
    bunching_vessels: int = Field(0, ge=0, le=20)
    schedule_shift_hours: float = Field(-6.0, ge=-48.0, le=48.0)
    parent_scenario_id: int | None = None


def _params(body: ExtendedScenarioBody) -> dict:
    return {
        "kind": body.kind,
        "crane_factor": body.crane_factor,
        "move_rate_per_crane_hour": body.move_rate_per_crane_hour,
        "terminal_code": body.terminal_code,
        "berth_count_delta": body.berth_count_delta,
        "bunching_vessels": body.bunching_vessels,
        "schedule_shift_hours": body.schedule_shift_hours,
    }


def _forecast_for_context(ctx: EngineContext, db: Session) -> dict:
    """Run the same weather-aware forecasting service on an in-memory scenario context.

    We deliberately do not persist scenario forecasts: scenario results are comparative
    what-if outputs. The forecast service itself is deterministic for a fixed context,
    and its cache key includes the context data_version.
    """
    return pipeline.run_forecasts(ctx)


@router.post("/scenarios", response_model=ScenarioResponse)
def scenario(body: ScenarioBody, db: Session = Depends(get_db)):
    scenario_params = {
        "crane_factor": body.crane_factor,
        "move_rate_per_crane_hour": body.move_rate_per_crane_hour,
        "kind": "CRANE_OUTAGE" if body.crane_factor < 1 else "PRODUCTIVITY",
    }
    ctx = pipeline.load_context(db)
    forecasts = pipeline.run_forecasts(ctx)
    base = pipeline.run_optimiser(ctx, forecasts, {})
    scen = pipeline.run_optimiser(ctx, forecasts, scenario_params)
    row = Scenario(name=f"{scenario_params['kind']} crane={body.crane_factor} rate={body.move_rate_per_crane_hour}", params=scenario_params, kind=scenario_params["kind"], status="APPLIED")
    db.add(row)
    db.flush()
    impact = ImpactAssessment(scenario_id=row.id, baseline=base["metrics"], scenario=scen["metrics"], deltas=scen_svc.compare(base["metrics"], scen["metrics"]), feasible=True)
    db.add(impact)
    db.commit()
    return {"scenario_id": row.id, "params": scenario_params, "baseline": base["metrics"], "scenario": scen["metrics"], "impact": impact.deltas, "weights": scen["weights"], "solver": {"baseline": base["solver"], "scenario": scen["solver"]}}


@router.post("/scenarios/extended", response_model=ScenarioExtendedResponse)
def scenario_extended(body: ExtendedScenarioBody, db: Session = Depends(get_db)):
    """W3 extended what-if: forecast and optimise the modified context, then compare."""
    ctx = pipeline.load_context(db)
    try:
        scen_ctx, description = scen_svc.modify_context(ctx, body)
    except scen_svc.ScenarioError as exc:
        raise HTTPException(400, str(exc)) from exc

    baseline_forecasts = _forecast_for_context(ctx, db)
    scenario_forecasts = _forecast_for_context(scen_ctx, db)
    params = {"crane_factor": body.crane_factor, "move_rate_per_crane_hour": body.move_rate_per_crane_hour}

    baseline = pipeline.run_optimiser(ctx, baseline_forecasts, {})
    scenario_out = pipeline.run_optimiser(scen_ctx, scenario_forecasts, params)
    impact = scen_svc.compare(baseline["metrics"], scenario_out["metrics"])

    row = Scenario(name=body.kind, params=_params(body), kind=body.kind, status="APPLIED", parent_scenario_id=body.parent_scenario_id)
    db.add(row)
    db.flush()
    db.add(ImpactAssessment(
        scenario_id=row.id,
        baseline=baseline["metrics"],
        scenario=scenario_out["metrics"],
        deltas=impact,
        feasible=bool(scenario_out["tidal_feasible"]),
    ))
    db.commit()

    return {
        "baseline": baseline["metrics"],
        "scenario": scenario_out["metrics"],
        "impact": impact,
        "feasible": bool(scenario_out["tidal_feasible"]),
        "kind": body.kind,
        "parent_scenario_id": body.parent_scenario_id,
        "scenario_id": row.id,
        "description": description,
        "forecast": {
            "baseline_data_version": ctx.data_version,
            "scenario_data_version": scen_ctx.data_version,
            "changed": ctx.data_version != scen_ctx.data_version,
            "baseline_zones": len(baseline_forecasts),
            "scenario_zones": len(scenario_forecasts),
        },
        "solver": {
            "baseline": baseline["solver"],
            "scenario": scenario_out["solver"],
            "scenario_status": scenario_out["status"],
        },
        "weights": scenario_out["weights"],
    }


@router.post("/scenarios/{scenario_id}/rollback", response_model=ScenarioRollbackResponse)
def scenario_rollback(scenario_id: int, db: Session = Depends(get_db)):
    row = db.get(Scenario, scenario_id)
    if row is None:
        raise HTTPException(404, f"scenario {scenario_id} not found")
    row.status = "ROLLED_BACK"
    db.commit()
    return {"restored": True, "scenario_id": scenario_id, "status": row.status}
