"""AIS ingestion and provenance management."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ais_track_model import AISTrack
from ..db import get_db
from ..models import CongestionObservation
from ..response_models import AisGenerateResponse, AisStatusResponse

router = APIRouter(prefix="/api/ais", tags=["ais"])
_MAX_BYTES = 50 * 1024 * 1024


@router.get("/status", response_model=AisStatusResponse)
def ais_status(db: Session = Depends(get_db)):
    total = db.execute(select(func.count()).select_from(CongestionObservation)).scalar() or 0
    tracks = db.execute(select(func.count()).select_from(AISTrack)).scalar() or 0
    if total == 0:
        return {"source": "EMPTY", "rows": 0, "zones": 0, "track_points": tracks, "newest_ts": None, "oldest_ts": None, "stub": False}
    row = db.execute(
        select(CongestionObservation.source, func.count().label("n"),
               func.max(CongestionObservation.ts).label("newest"), func.min(CongestionObservation.ts).label("oldest"))
        .group_by(CongestionObservation.source).order_by(func.count().desc())
    ).first()
    zones = db.execute(select(func.count(CongestionObservation.zone_code.distinct()))).scalar() or 0
    return {"source": row.source if row else "UNKNOWN", "rows": row.n if row else total, "zones": zones,
            "track_points": tracks, "newest_ts": row.newest.isoformat() if row and row.newest else None,
            "oldest_ts": row.oldest.isoformat() if row and row.oldest else None, "stub": False}


@router.post("/import")
async def ais_import(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import a real NOAA AccessAIS CSV, aggregate it, and retain filtered track points."""
    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="AIS file too large: maximum 50 MB")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="NOAA AccessAIS import requires a CSV file")
    raw_path = series_path = None
    try:
        from ..pipelines import ais as ais_pipeline
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as raw_f:
            raw_f.write(raw); raw_path = raw_f.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as series_f:
            series_path = series_f.name
        build_stats = ais_pipeline.build(raw_path, series_path, min_anchor_min=5.0, sog_max=1.0)
        dataset_id = f"NOAA-{hashlib.sha256(raw).hexdigest()[:24]}"
        track_stats = ais_pipeline.persist_tracks(raw_path, dataset_id=dataset_id, sog_max=1.0)
        import_stats = ais_pipeline.import_series(series_path, source="AIS", is_measured=True)
        db.expire_all()
        # Data-quality trigger (B-5): normalisation + completeness recompute after each
        # successful real-data import — the GET /api/quality endpoint stays read-only.
        try:
            from .quality import run_normalisation_pass
            normalised = run_normalisation_pass(db)
        except Exception:  # noqa: BLE001 — import must not fail because of the quality pass
            normalised = 0
        return {"status": "ok", "source": "AIS", "dataset_id": dataset_id,
                "message": "NOAA AccessAIS observations and filtered tracks imported",
                "build": build_stats, "tracks": track_stats, "import": import_stats,
                "normalised_rows_updated": normalised, "stub": False}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"AIS import failed: {exc}") from exc
    finally:
        if raw_path: Path(raw_path).unlink(missing_ok=True)
        if series_path: Path(series_path).unlink(missing_ok=True)


@router.post("/generate", response_model=AisGenerateResponse)
def ais_generate(days: int = Query(14, ge=7, le=30), seed: int = Query(20240817), db: Session = Depends(get_db)):
    """Generate synthetic DEMO_AIS data for an offline/reproducible demo."""
    from ..pipelines.ais_generate import generate_and_load
    stats = generate_and_load(days=days, seed=seed)
    return {"status": "ok", "source": "DEMO_AIS", "message": f"Synthetic DEMO_AIS history loaded: {stats.get('inserted', 0)} observations", **stats, "stub": False}
