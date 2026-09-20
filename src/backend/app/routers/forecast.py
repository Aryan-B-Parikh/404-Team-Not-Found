"""Forecast capability: LightGBM forecast, hotspots, model card, validation, confidence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import reference as ref
from ..config import get_settings
from ..db import get_db
from ..response_models import ForecastResponse
from ..serialize import forecast_to_dict
from ..services import forecasting as fc_svc
from ..services import pipeline

router = APIRouter(prefix="/api", tags=["forecast"])


@router.get("/forecast", response_model=ForecastResponse)
def forecast(db: Session = Depends(get_db), zone: str = Query("Z-PORT")):
    if zone not in ref.ALL_ZONES:
        raise HTTPException(400, f"unknown zone {zone}; expected one of {ref.ALL_ZONES}")
    full = pipeline.build_full(db, persist=False)

    # --- W2: consume W1 weather when FEATURE_WEATHER is on (never rebuild the pipeline) ---
    if get_settings().feature_weather:
        weather = fc_svc.load_weather_series(db, full["ctx"].t0)
        if weather:
            for f in full["forecasts"].values():
                fc_svc.apply_weather_adjustment(f, weather)

    sel = full["forecasts"][zone]
    selected = forecast_to_dict(sel)
    # per-target prediction intervals (additive; serialize.py stays Integrator-owned)
    for pd, p in zip(selected["points"], sel.points):
        pd["queue_lo"], pd["queue_hi"] = p.queue_lo, p.queue_hi
        pd["wait_lo"], pd["wait_hi"] = p.wait_lo, p.wait_hi
        pd["yard_lo"], pd["yard_hi"] = p.yard_lo, p.yard_hi
    selected["weather_used"] = sel.weather_used
    selected["confidence"] = sel.confidence
    selected["confidence_by_horizon"] = sel.confidence_by_horizon
    selected["horizons"] = sel.horizons
    selected["data_version"] = sel.data_version

    return {
        "t0": full["ctx"].t0.isoformat(),
        "dataset_source": full["ctx"].dataset_source,
        "summary": {z: {"zone_name": f.zone_name, "current": f.current, "peak": f.peak,
                        "avg_index": f.avg_index} for z, f in full["forecasts"].items()},
        "selected": selected,
        "hotspots": full["hotspots"],
        "anomalies": full["anomalies"],
        # --- Phase 0 frozen keys (now real) + W2 additive keys ---
        "weather_used": sel.weather_used,
        "confidence": sel.confidence,
        "confidence_by_horizon": sel.confidence_by_horizon,
        "horizons": sel.horizons,
        "provenance": {
            "model_version": sel.model.get("model_version"),
            "data_version": sel.data_version,
            "feature_flags": sel.model.get("feature_flags", {}),
        },
    }
