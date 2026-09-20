"""Contract-drift tripwire (process audit rec #3).

The API contract previously had two owners: backend dataclasses and the
hand-written frontend Zod schemas (src/frontend/src/lib/schemas.ts). They
drifted — ``yard_util`` vs ``yard_util_pct``, hotspot ``confidence`` string vs
number — and the drift degraded silently (Zod warnings discarded, blank UI).

Full contract generation from OpenAPI is tracked in docs/backlog.md (rec #3).
Until then these DB-gated tests pin the fields the frontend schema reads, so
renaming a backend key fails CI with a message pointing at the frontend file
that must change with it.
"""

from __future__ import annotations

import pytest

from .conftest import requires_db

pytestmark = [pytest.mark.slow, requires_db]  # builds the full engine stack (~16s)

@requires_db
def test_zone_payload_fields_match_frontend_schema(client):
    """These keys are load-bearing in src/frontend/src/lib/schemas.ts ZoneSchema."""
    r = client.get("/api/overview")
    assert r.status_code == 200
    zones = r.json().get("zones") or []
    assert zones, "overview must expose zones"
    required = {"zone_code", "label", "current_index", "peak_index", "peak_hour",
                "queue_now", "wait_now", "yard_util_pct", "recent_index"}
    missing = required - set(zones[0])
    assert not missing, (
        f"Backend zone payload is missing {sorted(missing)} — update "
        f"src/frontend/src/lib/schemas.ts ZoneSchema in the same commit if you "
        f"renamed a field intentionally."
    )


@requires_db
def test_hotspot_confidence_is_numeric(client):
    """Frontend renders confidence as a number; a string re-introduces the old drift."""
    r = client.get("/api/overview")
    assert r.status_code == 200
    ranked = (r.json().get("hotspots") or {}).get("ranked") or []
    assert ranked, "overview must expose ranked hotspots"
    for h in ranked:
        assert isinstance(h.get("confidence"), (int, float)), (
            f"hotspot confidence must be numeric, got {type(h.get('confidence'))}: "
            f"{h.get('confidence')!r} — schemas.ts expects a number"
        )
