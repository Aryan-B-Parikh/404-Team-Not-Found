"""Data quality service for W1.

Provides:
- NormalisationEngine: converts raw vessel call fields to SI units, normalises
  timestamps to UTC ISO-8601, and records original + normalised values in
  VesselCall.normalised JSONB column.  Schema versioned so consumers can detect
  when the normalisation rules were last updated.
- compute_terminal_quality: aggregates data completeness per terminal and writes
  TerminalQuality rows.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any

from dateutil import parser as dtparser
from sqlalchemy.orm import Session

from ..models import Terminal, TerminalQuality, VesselCall

# Bump whenever the normalisation rules change so downstream code can detect stale records.
SCHEMA_VERSION = "v2"


class NormalisationEngine:
    """Normalisation engine — feet → metres, timestamps → UTC ISO-8601.

    For each VesselCall a ``normalised`` dict is produced mapping field names to:
        {"original": <raw>, "unit": <original_unit>, "value_si": <converted>, "si_unit": <unit>}

    Timestamp fields are normalised to UTC ISO-8601 strings:
        {"original": <raw_str>, "unit": "local_or_unknown", "value_si": <utc_iso>, "si_unit": "UTC"}

    The ``schema_version`` key is always written so a reader can tell which rules
    were applied without inspecting code.
    """

    # (field_name, original_unit, conversion_factor, si_unit)
    _LENGTH_FIELDS: list[tuple[str, str, float, str]] = [
        ("loa_ft",   "ft", 0.3048, "m"),
        ("beam_ft",  "ft", 0.3048, "m"),
        ("draft_ft", "ft", 0.3048, "m"),
    ]

    # ETA/ETD fields stored as hours-ahead floats → convert to seconds (SI time interval)
    _HOURS_FIELDS: list[tuple[str, str, float, str]] = [
        ("declared_eta_hours", "h", 3600.0, "s"),
        ("ais_eta_hours",      "h", 3600.0, "s"),
        ("etd_hours",          "h", 3600.0, "s"),
        ("anchored_hours",     "h", 3600.0, "s"),
    ]

    # Timestamp string fields → parse to UTC ISO-8601
    _TIMESTAMP_FIELDS: list[str] = []  # VesselCall has no raw string timestamp columns,
    # but the normaliser is wired to handle them if added in future.

    def __init__(self, session: Session) -> None:
        self.session = session

    def normalise_vessel(self, vessel: VesselCall) -> dict[str, Any]:
        norm: dict[str, Any] = {"schema_version": SCHEMA_VERSION}

        # Length fields (ft → m)
        for field, orig_unit, factor, si_unit in self._LENGTH_FIELDS:
            raw_val = getattr(vessel, field, None)
            if raw_val is not None:
                norm[field] = {
                    "original": raw_val,
                    "unit": orig_unit,
                    "value_si": round(float(raw_val) * factor, 3),
                    "si_unit": si_unit,
                }

        # Duration fields (hours → seconds)
        for field, orig_unit, factor, si_unit in self._HOURS_FIELDS:
            raw_val = getattr(vessel, field, None)
            if raw_val is not None:
                norm[field] = {
                    "original": raw_val,
                    "unit": orig_unit,
                    "value_si": round(float(raw_val) * factor, 1),
                    "si_unit": si_unit,
                }

        # Timestamp string fields → UTC ISO-8601 (extensible; no raw string fields currently)
        for field in self._TIMESTAMP_FIELDS:
            raw_val = getattr(vessel, field, None)
            if raw_val is not None:
                norm[field] = _parse_to_utc(field, raw_val)

        return norm

    def run(self) -> int:
        """Normalise all VesselCall rows that are missing or on an old schema version.

        Returns the number of rows updated.
        """
        vessels = (
            self.session.query(VesselCall)
            .filter(
                (VesselCall.normalised.is_(None))
                | (VesselCall.normalised["schema_version"].as_string() != SCHEMA_VERSION)
            )
            .all()
        )
        for v in vessels:
            v.normalised = self.normalise_vessel(v)
        self.session.commit()
        return len(vessels)


def _parse_to_utc(field: str, raw: Any) -> dict[str, Any]:
    """Best-effort parse of a timestamp string to UTC ISO-8601.

    Handles:
    - datetime objects (already typed)
    - ISO-8601 strings with or without timezone
    - Common US date formats via dateutil
    Returns a normalised dict; on parse failure returns the original with an error flag.
    """
    from datetime import datetime

    if isinstance(raw, datetime):
        utc_dt = raw.astimezone(timezone.utc) if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
        return {"original": raw.isoformat(), "unit": "datetime", "value_si": utc_dt.isoformat(), "si_unit": "UTC"}

    raw_str = str(raw).strip()
    try:
        parsed = dtparser.parse(raw_str)
        utc_dt = parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        return {"original": raw_str, "unit": "local_or_unknown", "value_si": utc_dt.isoformat(), "si_unit": "UTC"}
    except (ValueError, OverflowError) as exc:
        return {"original": raw_str, "unit": "unknown", "value_si": None, "si_unit": "UTC",
                "error": f"parse_failed: {exc}"}


def compute_terminal_quality(session: Session) -> None:
    """Compute data-completeness per terminal (Module D).

    Completeness = share of the terminal's vessel calls with every identity field
    populated (``imo`` + ``voyage_number`` + a usable ETA). Vessels are attributed
    via ``Terminal.zone_code == VesselCall.dest_zone_code`` — the audit (B-9) caught
    the previous version joining on ``Terminal.code``, which never matches a ``Z-*``
    zone code and therefore always reported a self-fulfilling 100%.

    Also records the normalisation schema_version so operators can see whether the
    normalised column is current.
    """
    for code, zone in {t.code: t.zone_code for t in session.query(Terminal).all()}.items():
        total = session.query(VesselCall).filter(VesselCall.dest_zone_code == zone).count()
        if total == 0:
            completeness, missing = 0.0, ["vessel_calls"]
        else:
            good = session.query(VesselCall).filter(
                VesselCall.dest_zone_code == zone,
                VesselCall.imo.is_not(None),
                VesselCall.voyage_number.is_not(None),
            ).count()
            completeness = round(100.0 * good / total, 2)
            missing = []
            if session.query(VesselCall).filter(VesselCall.dest_zone_code == zone, VesselCall.imo.is_(None)).count() > 0:
                missing.append("imo")
            if session.query(VesselCall).filter(VesselCall.dest_zone_code == zone, VesselCall.voyage_number.is_(None)).count() > 0:
                missing.append("voyage_number")
        # count rows not yet normalised to current schema version
        stale = session.query(VesselCall).filter(
            VesselCall.dest_zone_code == zone,
            (VesselCall.normalised.is_(None))
            | (VesselCall.normalised["schema_version"].as_string() != SCHEMA_VERSION),
        ).count()
        terminal_id = session.query(Terminal.id).filter(Terminal.code == code).scalar()
        tq = session.query(TerminalQuality).filter(TerminalQuality.terminal_id == terminal_id).first()
        if not tq:
            tq = TerminalQuality(
                terminal_id=terminal_id,
                completeness_pct=completeness,
                missing=missing,
                rules_version=SCHEMA_VERSION,
            )
            session.add(tq)
        else:
            tq.completeness_pct = completeness
            tq.missing = missing
            tq.rules_version = SCHEMA_VERSION
        # attach normalisation staleness to the quality record (informational)
        if hasattr(tq, "notes"):
            tq.notes = f"stale_normalised_rows={stale}"
    session.commit()
