"""FastAPI gateway — mounts every capability router behind one app."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text

from .config import get_settings
from .db import SessionLocal, ensure_schema
from .models import Terminal
from .response_models import HealthResponse
from .routers import ALL_ROUTERS

_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()
    db = SessionLocal()
    try:
        if db.execute(select(func.count()).select_from(Terminal)).scalar() == 0:
            print("[startup] empty database — seeding real POLB reference data + DEMO_AIS simulation layer…")
            from .seed import seed
            seed()
            db.expire_all()

        try:
            ais_count = db.execute(text("SELECT COUNT(*) FROM congestion_observation WHERE source='AIS'")).scalar() or 0
            demo_count = db.execute(text("SELECT COUNT(*) FROM congestion_observation WHERE source='DEMO_AIS'")).scalar() or 0
            if ais_count:
                print(f"[startup] operational dataset: AIS ({ais_count} observations)")
            elif demo_count:
                print(f"[startup] operational dataset: DEMO_AIS ({demo_count} observations)")
            else:
                print("[startup] warning: no congestion observations available")
        except Exception as exc:  # noqa: BLE001
            print(f"[startup] dataset status check skipped: {exc}")

        # Tides are a safety constraint. Prefer NOAA CO-OPS predictions whenever reachable;
        # otherwise retain the explicitly labelled harmonic model rather than pretending it is observed.
        try:
            from .services import tides
            latest = db.execute(text("SELECT MAX(ts) FROM congestion_observation")).scalar()
            tide_rows = tides.fetch_noaa_tides(db, horizon_hours=96, t0=latest)
            if tide_rows:
                print(f"[startup] tide pipeline: NOAA CO-OPS ({tide_rows} rows)")
            else:
                tide_rows = tides.ensure_windows(db, horizon_hours=96, t0=latest)
                print(f"[startup] tide pipeline: harmonic-model fallback ({tide_rows} rows)")
        except Exception as exc:  # noqa: BLE001
            print(f"[startup] tide pipeline unavailable: {exc}")

        try:
            from .pipelines.weather import run_weather_pipeline
            n = run_weather_pipeline(db, hours=72)
            if n:
                print(f"[startup] weather pipeline: {n} rows from Open-Meteo")
        except Exception as exc:  # noqa: BLE001
            print(f"[startup] weather pipeline skipped: {exc}")

        # B-5: normalisation is an explicit pass (startup + POST /api/quality/refresh),
        # never a GET side effect. Completeness is computed here so /api/quality reads
        # a fresh snapshot without writing.
        try:
            from .routers.quality import run_normalisation_pass
            n = run_normalisation_pass(db)
            print(f"[startup] data-quality pass: normalised {n} rows")
        except Exception as exc:  # noqa: BLE001
            print(f"[startup] data-quality pass skipped: {exc}")
    finally:
        db.close()
    yield


app = FastAPI(title="PortPulse AI API", version="0.1.0",
              description="PortPulse AI: forecasting, anomalies, CP-SAT optimisation, routing, and IBM Bob agent orchestration.",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_list,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
for r in ALL_ROUTERS:
    app.include_router(r)


@app.get("/health", tags=["meta"], response_model=HealthResponse)
def health():
    return {"status": "ok"}


# Serverless alias: Vercel's Python builder only routes /api/* to the function,
# so the same health payload is exposed under the /api prefix.
@app.get("/api/health", tags=["meta"], response_model=HealthResponse, include_in_schema=False)
def health_api():
    return {"status": "ok"}


if _DIST.is_dir():
    from fastapi.responses import FileResponse

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def spa_fallback(full_path: str):
        """SPA deep links (B-3): /forecast, /berth, … must serve the app shell.
        Real files (JS/CSS assets) are served directly; everything else gets
        index.html so the client router picks up the tab from the pathname."""
        candidate = (_DIST / full_path).resolve()
        if full_path and candidate.is_file() and str(candidate).startswith(str(_DIST.resolve())):
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
