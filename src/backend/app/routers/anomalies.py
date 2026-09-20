"""Anomaly detection capability (W2) — moved out of catalog.py in Phase 0.

FROZEN SHAPE: {anomalies:[{zone_code, kind, method, score, is_anomaly, sample_size, detail, features}]}
W2 additive top-level keys: weather_used, method, generated_at.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..response_models import AnomaliesResponse
from ..services import anomaly as anomaly_svc
from ..services import forecasting as fc_svc
from ..services import pipeline

router = APIRouter(prefix="/api", tags=["anomalies"])


@router.get("/anomalies", response_model=AnomaliesResponse)
def anomalies(db: Session = Depends(get_db)):
    full = pipeline.build_full(db, persist=False)
    anomalies = full["anomalies"]
    weather_used = False

    # Consume W1 weather when FEATURE_WEATHER is on (re-detects with the weather signal).
    if get_settings().feature_weather:
        weather = fc_svc.load_weather_series(db, full["ctx"].t0)
        if weather:
            anomalies = anomaly_svc.detect_anomalies(full["ctx"], weather=weather)
            weather_used = any(a.get("weather_used") for a in anomalies)

    return {
        "anomalies": anomalies,
        "weather_used": weather_used,
        "method": "IsolationForest",
        "generated_at": full["ctx"].t0.isoformat(),
    }
