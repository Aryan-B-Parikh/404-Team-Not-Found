"""Raw/filtered AIS point storage for real NOAA AccessAIS imports."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class AISTrack(Base):
    __tablename__ = "ais_track"
    __table_args__ = (
        Index("ix_ais_track_mmsi_ts", "mmsi", "ts"),
        Index("ix_ais_track_zone_ts", "zone_code", "ts"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(80), index=True)
    mmsi: Mapped[str] = mapped_column(String(16), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    sog: Mapped[float | None] = mapped_column(Float)
    cog: Mapped[float | None] = mapped_column(Float)
    zone_code: Mapped[str | None] = mapped_column(String(16), index=True)
    raw: Mapped[dict | None] = mapped_column(JSONB)
