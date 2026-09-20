"""Database engine, session factory and declarative base (SQLAlchemy 2.0 + psycopg3)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()


def _normalise_database_url(url: str) -> str:
    """Map managed-Postgres URL schemes onto the psycopg3 driver.

    Managed providers (Voroa/Render/Heroku) hand out ``postgresql://`` or
    ``postgres://`` URLs; SQLAlchemy's default dialect would try psycopg2, which
    is not installed. Rewrite them to ``postgresql+psycopg://`` (psycopg3). An
    explicit ``+psycopg`` in the URL is preserved.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _engine_kwargs() -> dict:
    """Engine kwargs with managed-Postgres safety toggles (Supabase et al.).

    ``DB_PGBOUNCER=true`` disables named prepared statements (psycopg3
    ``prepare_threshold=None``) so the engine can sit behind PgBouncer in
    transaction-pooling mode (Supabase pooler :6543). ``DB_SSL=true`` forces
    ``sslmode=require`` (Supabase rejects plaintext connections).
    """
    kwargs: dict = {"echo": settings.db_echo, "pool_pre_ping": True, "future": True}
    if _normalise_database_url(settings.database_url).startswith("sqlite"):
        return kwargs
    connect_args: dict = {}
    if settings.db_pgbouncer:
        connect_args["prepare_threshold"] = None
    if settings.db_ssl:
        connect_args["sslmode"] = "require"
    if connect_args:
        kwargs["connect_args"] = connect_args
    return kwargs


engine = create_engine(_normalise_database_url(settings.database_url), **_engine_kwargs())
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
