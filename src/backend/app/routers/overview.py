"""Overview capability: live KPIs, zone status, alerts, hotspots, anomalies."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..response_models import Overview
from ..services import pipeline

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview", response_model=Overview)
def overview(db: Session = Depends(get_db)):
    full = pipeline.build_full(db, persist=False)
    return pipeline.build_overview(full["ctx"], full["forecasts"], full["hotspots"],
                                   full["anomalies"], full["optimiser"])
