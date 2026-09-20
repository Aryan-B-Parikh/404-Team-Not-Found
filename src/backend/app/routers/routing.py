"""Routing capability: alternate-routing recommendations."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from .. import reference as ref
from ..response_models import RoutingResponse
from ..services import pipeline, routing as services

router = APIRouter(prefix="/api", tags=["routing"])


@router.get("/routing", response_model=RoutingResponse)
def routing(db: Session = Depends(get_db)):
    full = pipeline.build_full(db, persist=False)
    recs = full["routing"]
    counts: dict[str, int] = {}
    for r in recs:
        counts[r["option"]] = counts.get(r["option"], 0) + 1
    return {"recommendations": recs, "counts": counts,
            "total_savings_usd": sum(r["est_savings_usd"] for r in recs),
            "cost_model": {"daily_op_cost_usd": 32000, "reefer_value_usd": 180,
                           "alt_ports": [p["name"] for p in ref.ALT_PORTS],
                           "basis": "indicative planning estimates — linear formulas over "
                                    "public mid-range references (reference.py), not carrier "
                                    "quotes or berth-fee quotations; external-port availability "
                                    "comes from the operator-supplied PORT_STATUS_JSON feed",
                           "formulas": services.ASSUMPTIONS}}
