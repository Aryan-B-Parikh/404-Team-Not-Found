"""72-hour operations plan and CSV exports; IBM Bob provides optional narrative."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import OperationsPlan
from ..response_models import PlanResponse
from ..services import pipeline

router = APIRouter(prefix="/api", tags=["plan"])


@router.get("/plan", response_model=PlanResponse)
def get_plan(db: Session = Depends(get_db), text: int = Query(0), persist: int = Query(0)):
    """Return the latest persisted plan or build a fresh engine-grounded plan."""
    latest = db.execute(select(OperationsPlan).order_by(OperationsPlan.id.desc())).scalars().first()
    if latest is not None and not persist:
        summary = dict(latest.summary or {})
        summary.setdefault("confidence_by_bucket", {})
        # Spec §6 traceability: the plan row stores its source-run lineage; serve it
        # so every number is traceable to the snapshot that produced it.
        out = {"summary": summary, "shifts": latest.shifts or [], "text": latest.text_plan,
               "narrative_source": latest.narrative_source or "deterministic",
               "plan_id": latest.id,
               "created_at": latest.created_at.isoformat() if latest.created_at else None,
               "forecast_run_id": latest.forecast_run_id,
               "optimiser_run_id": latest.optimiser_run_id}
        # Playtest fix: narrative_source was None on the read path even though the
        # plan text itself is deterministic engine output — the UI showed no provenance.
        if text:
            return PlainTextResponse(out["text"])
        return out
    full = pipeline.build_full(db, persist=bool(persist))
    out = full["plan"]
    out["summary"].setdefault("confidence_by_bucket", {})
    if persist:
        pipeline.persist_plan(db, out)
    # persist=False means the text was produced by the deterministic builder (LLM never invoked)
    out.setdefault("narrative_source", "deterministic")
    out["plan_id"] = None
    out["created_at"] = None
    out["forecast_run_id"] = out["summary"].get("forecast_run_id")
    out["optimiser_run_id"] = out["summary"].get("optimiser_run_id")
    if text:
        return PlainTextResponse(out["text"])
    return out


@router.post("/plan")
def regenerate(db: Session = Depends(get_db)):
    full = pipeline.build_full(db, persist=True)
    full["plan"]["summary"].setdefault("confidence_by_bucket", {})
    plan_id = pipeline.persist_plan(db, full["plan"])
    return {**full["plan"], "plan_id": plan_id}


@router.get("/export")
def export(db: Session = Depends(get_db), type: str = Query("assignments")):
    full = pipeline.build_full(db, persist=False)
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    if type == "assignments":
        w.writerow(["vessel", "carrier", "berth", "terminal", "start_hour", "end_hour", "cranes", "wait_hours"])
        for a in full["optimiser"]["assignments"]:
            w.writerow([a["vessel_name"], a["carrier"], a["berth_name"], a["terminal_code"], a["start_hour"], a["end_hour"], a["cranes"], a["wait_hours"]])
    elif type == "routing":
        w.writerow(["vessel", "option", "target_port", "predicted_wait_h", "eta_shift_h", "savings_usd", "tier"])
        for r in full["routing"]:
            w.writerow([r["vessel_name"], r["option"], r.get("target_port") or "", r["predicted_wait_hours"], r.get("eta_shift_hours", 0), r["est_savings_usd"], r["tier"]])
    elif type == "vessels":
        w.writerow(["name", "mmsi", "carrier", "class", "loa_ft", "draft_ft", "moves", "reefers", "status", "anchored_h", "eta_h"])
        for v in full["ctx"].vessels:
            w.writerow([v.name, v.mmsi, v.carrier, v.vessel_class, v.loa_ft, v.draft_ft, v.total_moves, v.reefer_units, v.status, v.anchored_hours, v.eta_hours])
    elif type == "forecast":
        w.writerow(["zone", "hour", "ts", "index", "queue", "wait", "yard_util", "lo", "hi"])
        for z, fc in full["forecasts"].items():
            for p in fc.points:
                w.writerow([z, p.hour, p.ts.isoformat(), p.index, p.queue, p.wait, p.yard_util, p.lo, p.hi])
    else:
        w.writerow(["error"])
        w.writerow([f"unknown type {type}"])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{type}.csv"'})
