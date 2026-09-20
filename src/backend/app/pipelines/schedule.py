"""Validated vessel-schedule ingestion."""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

LOGGER = logging.getLogger(__name__)
_REQUIRED_COLUMNS = {
    "imo", "voyage_number", "declared_eta_hours", "loa_ft", "beam_ft", "draft_ft",
    "teu_capacity", "import_moves", "export_moves", "dest_zone_code",
}
_NUMERIC_FIELDS = {
    "declared_eta_hours": float, "loa_ft": float, "beam_ft": float, "draft_ft": float,
    "teu_capacity": float, "import_moves": float, "export_moves": float, "reefer_units": float,
}


def _positive_number(row: dict[str, Any], field: str) -> float:
    raw = (row.get(field) or "").strip()
    if raw == "":
        raise ValueError(f"{field} is empty")
    value = _NUMERIC_FIELDS[field](raw)
    if value <= 0 and field not in {"reefer_units"}:
        raise ValueError(f"{field} must be > 0")
    if field in {"teu_capacity", "import_moves", "export_moves", "reefer_units"} and value != int(value):
        raise ValueError(f"{field} must be an integer")
    return value


def parse_schedule(csv_bytes: bytes) -> dict[str, Any]:
    """Parse CSV bytes and return accepted/rejected rows without losing row-level diagnostics."""
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"schedule CSV must be UTF-8: {exc}") from exc

    with io.StringIO(text, newline="") as f:
        reader = csv.DictReader(f)
        fields = {str(x).strip() for x in (reader.fieldnames or []) if x}
        missing_columns = _REQUIRED_COLUMNS - fields
        for line_no, raw_row in enumerate(reader, start=2):
            row = {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items() if k is not None}
            try:
                if missing_columns:
                    raise ValueError(f"missing required columns: {', '.join(sorted(missing_columns))}")
                if not row.get("imo"):
                    raise ValueError("imo is empty")
                if not row.get("voyage_number"):
                    raise ValueError("voyage_number is empty")
                if not row.get("dest_zone_code"):
                    raise ValueError("dest_zone_code is empty")
                for field in _REQUIRED_COLUMNS - {"imo", "voyage_number", "dest_zone_code"}:
                    _positive_number(row, field)
                row["declared_eta_hours"] = float(row["declared_eta_hours"])
                row["loa_ft"] = int(float(row["loa_ft"]))
                row["beam_ft"] = int(float(row["beam_ft"]))
                row["draft_ft"] = float(row["draft_ft"])
                for field in ("teu_capacity", "import_moves", "export_moves"):
                    row[field] = int(float(row[field]))
                row["reefer_units"] = int(float(row["reefer_units"])) if row.get("reefer_units") else 0
                accepted.append(row)
            except (ValueError, TypeError, OverflowError) as exc:
                LOGGER.warning("Invalid row %d in schedule CSV: %s", line_no, exc)
                rejected.append({"row_no": line_no, "row": row, "error": str(exc)})
    return {"accepted": accepted, "rejected": rejected, "rows": len(accepted) + len(rejected)}
