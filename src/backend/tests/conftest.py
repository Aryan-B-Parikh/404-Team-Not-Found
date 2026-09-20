"""Shared test fixtures.

DB-backed tests are skipped automatically when PostgreSQL is unreachable, so
`uv run pytest -q` passes on a machine without the database.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text


def _db_available() -> bool:
    try:
        from app.db import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


DB_AVAILABLE = _db_available()
requires_db = pytest.mark.skipif(not DB_AVAILABLE, reason="PostgreSQL not reachable")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
