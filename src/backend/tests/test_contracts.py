"""Contract tests — the merge gate.

`test_frozen_paths_present` needs no database and catches route removals/renames.
The shape tests run only when PostgreSQL is reachable.
"""

from __future__ import annotations

import pytest

from app.main import app

from .conftest import requires_db

pytestmark = pytest.mark.slow  # DB/live-engine contract tests (~35s)

FROZEN_PATHS = [
    "/health",
    "/api/overview",
    "/api/forecast",
    "/api/optimise",
    "/api/optimise/latest",
    "/api/scenarios",
    "/api/scenarios/extended",
    "/api/scenarios/{scenario_id}/rollback",
    "/api/routing",
    "/api/plan",
    "/api/terminals",
    "/api/vessels",
    "/api/vessels/upload",
    "/api/anomalies",
    "/api/hotspots",
    "/api/quality",
    "/api/weather",
    "/api/export",
    "/api/bob",
]


def test_frozen_paths_present():
    """Every frozen path must exist in the OpenAPI schema (no DB needed)."""
    paths = app.openapi()["paths"]
    missing = [p for p in FROZEN_PATHS if p not in paths]
    assert not missing, f"frozen API paths missing: {missing}"


def test_no_path_removed_from_contract():
    """Guard against accidental renames: the documented methods must be present."""
    paths = app.openapi()["paths"]
    expected_methods = {
        "/api/quality": {"get"},
        "/api/weather": {"get"},
        "/api/vessels/upload": {"post"},
        "/api/anomalies": {"get"},
        "/api/scenarios/extended": {"post"},
        "/api/scenarios/{scenario_id}/rollback": {"post"},
    }
    for path, methods in expected_methods.items():
        got = set(paths.get(path, {}).keys())
        assert methods <= got, f"{path} must expose {methods}, got {got}"


@requires_db
def test_quality_shape(client):
    r = client.get("/api/quality")
    assert r.status_code == 200
    body = r.json()
    assert {"terminals", "rules_version"} <= set(body)
    assert isinstance(body["terminals"], list)
    for t in body["terminals"]:
        assert {"terminal_code", "name", "completeness_pct", "missing"} <= set(t)


@requires_db
def test_weather_shape(client):
    body = client.get("/api/weather?hours=72").json()
    assert {"points", "source", "hours"} <= set(body)
    assert isinstance(body["points"], list)


@requires_db
def test_forecast_frozen_keys(client):
    body = client.get("/api/forecast?zone=Z-PORT").json()
    assert {"t0", "dataset_source", "summary", "selected", "weather_used", "confidence"} <= set(body)
    assert len(body["selected"]["points"]) == 72


@requires_db
def test_optimise_frozen_keys(client):
    body = client.post("/api/optimise", json={"crane_factor": 1.0, "move_rate_per_crane_hour": 28}).json()
    assert {"solver", "status", "assignments", "metrics", "baseline", "deltas", "tidal_feasible",
            "incremental"} <= set(body)
    assert body["solver"] == "ortools-cp-sat"


@requires_db
def test_plan_frozen_keys(client):
    body = client.get("/api/plan").json()
    assert {"summary", "shifts", "text"} <= set(body)
    assert "confidence_by_bucket" in body["summary"]
    assert len(body["shifts"]) == 12


@requires_db
def test_anomalies_moved_to_own_router(client):
    body = client.get("/api/anomalies").json()
    assert "anomalies" in body


@requires_db
def test_quality_get_is_idempotent(client):
    """B-5: GET /api/quality must not write. Two GETs return identical bodies and
    leave no new TerminalQuality rows (the write side lives at startup and POST)."""
    from sqlalchemy import func, select
    from app.models import TerminalQuality
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        before = db.execute(select(func.count()).select_from(TerminalQuality)).scalar()
    finally:
        db.close()
    r1 = client.get("/api/quality")
    r2 = client.get("/api/quality")
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json(), "two consecutive GETs must return identical bodies"
    assert "normalised_rows_updated" not in r1.json()
    db = SessionLocal()
    try:
        after = db.execute(select(func.count()).select_from(TerminalQuality)).scalar()
    finally:
        db.close()
    assert after == before, "GET must not create TerminalQuality rows"


@requires_db
def test_quality_refresh_is_the_write_path(client):
    """POST /api/quality/refresh is the explicit recompute; GET stays read-only."""
    r = client.post("/api/quality/refresh")
    assert r.status_code == 200
    assert {"status", "normalised_rows_updated"} <= set(r.json())


@requires_db
def test_tides_get_is_idempotent(client):
    """§11: GET /api/tides must not write. The NOAA fetch and window ensure live at
    startup (main.py) and POST /api/tides/refresh; the read path only serves the
    persisted rows (or the labelled harmonic model when none exist)."""
    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.models import TidalWindow

    db = SessionLocal()
    try:
        before = db.execute(select(func.count()).select_from(TidalWindow)).scalar()
    finally:
        db.close()
    r1 = client.get("/api/tides?hours=48")
    r2 = client.get("/api/tides?hours=48")
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json(), "two consecutive GETs must return identical bodies"
    assert "noaa_rows_written" not in r1.json(), "write-side key must not leak on the read path"
    db = SessionLocal()
    try:
        after = db.execute(select(func.count()).select_from(TidalWindow)).scalar()
    finally:
        db.close()
    assert after == before, "GET must not create TidalWindow rows"


@requires_db
def test_tides_refresh_is_the_write_path(client):
    """POST /api/tides/refresh is the explicit recompute; GET stays read-only."""
    r = client.post("/api/tides/refresh")
    assert r.status_code == 200
    assert {"source", "rows_written", "station"} <= set(r.json())


@requires_db
def test_plan_get_serves_provenance(client):
    """Spec §6: a persisted plan must expose its snapshot lineage (run ids, created_at)."""
    body = client.get("/api/plan").json()
    assert {"plan_id", "created_at", "forecast_run_id", "optimiser_run_id"} <= set(body)
    if body["plan_id"] is not None:  # persisted path: lineage must be populated
        assert body["created_at"] is not None


@requires_db
def test_upload_stub_shape(client):
    body = client.post("/api/vessels/upload", files={"file": ("schedule.csv", "a,b\n1,2\n", "text/csv")}).json()
    assert {"accepted", "rejected", "errors", "revisions_created"} <= set(body)


@requires_db
def test_ais_generate_shape_matches_strict_model(client, monkeypatch):
    """The generate response model must accept the exact keys the pipeline returns.
    Generator is monkeypatched — the real one replaces the congestion history."""
    from app.pipelines import ais_generate

    monkeypatch.setattr(ais_generate, "generate_and_load", lambda days=14, seed=20240817: {
        "rows_scanned": 4, "skipped": 0, "vessels": 1, "hours": 25.0, "output_rows": 10,
        "inserted": 10, "source": "DEMO_AIS", "is_measured": False, "zones": 1,
        "newest_ts": "2026-09-20T00:00:00+00:00", "days": days, "seed": seed,
    })
    body = client.post("/api/ais/generate?days=14&seed=7").json()
    assert {"status", "source", "message", "rows_scanned", "inserted", "zones", "vessels", "stub"} <= set(body)
    assert body["source"] == "DEMO_AIS"


@requires_db
def test_scenario_extended_shape(client):
    body = client.post("/api/scenarios/extended", json={"kind": "CRANE_OUTAGE"}).json()
    assert {"baseline", "scenario", "impact", "feasible"} <= set(body)
    assert {"serviced", "moves", "avg_wait", "makespan"} <= set(body["impact"])


@requires_db
def test_scenario_extended_validates_contradictions(client):
    # L requirement: contradictory parameters must not be applied silently
    r = client.post("/api/scenarios/extended", json={"kind": "BERTH_REMOVED", "terminal_code": "PCT"})
    assert r.status_code == 400
