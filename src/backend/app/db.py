"""Database engine, session factory and declarative base (SQLAlchemy 2.0 + psycopg3)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=settings.db_echo, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all application tables, including the real-AIS track store."""
    from . import ais_track_model, models  # noqa: F401

    Base.metadata.create_all(bind=engine)


_NEW_COLUMNS = [
    "ALTER TABLE vessel_call ADD COLUMN IF NOT EXISTS voyage_number VARCHAR(40)",
    "ALTER TABLE vessel_call ADD COLUMN IF NOT EXISTS normalised JSONB",
    "ALTER TABLE forecast_run ADD COLUMN IF NOT EXISTS data_version VARCHAR(64)",
    "ALTER TABLE forecast_run ADD COLUMN IF NOT EXISTS feature_flags JSONB",
    "ALTER TABLE routing_recommendation ADD COLUMN IF NOT EXISTS option_detail JSONB",
    "ALTER TABLE operations_plan ADD COLUMN IF NOT EXISTS confidence_json JSONB",
    "ALTER TABLE scenario ADD COLUMN IF NOT EXISTS parent_scenario_id INTEGER",
    "ALTER TABLE scenario ADD COLUMN IF NOT EXISTS status VARCHAR(16) DEFAULT 'DRAFT'",
]


def ensure_schema() -> None:
    """Create new tables and add frozen additive columns idempotently."""
    from sqlalchemy import text

    init_db()
    with engine.begin() as conn:
        for stmt in _NEW_COLUMNS:
            conn.execute(text(stmt))


def drop_all() -> None:
    from . import ais_track_model, models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
