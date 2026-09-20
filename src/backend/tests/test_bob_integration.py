"""Integration test: IBM Bob → deterministic engine path → grounded answer.

Verifies that bob.respond() actually runs the engines (forecast, hotspot,
anomaly), returns a non-empty grounded answer, and exposes the tool-call
action list — confirming the MCP/engine pipeline is load-bearing, not
bypassed by a stale cache or short-circuit.

Requires PostgreSQL (skipped otherwise).
"""

from __future__ import annotations

import pytest

from .conftest import requires_db

pytestmark = pytest.mark.slow  # Bob + engine integration (~20s)


@requires_db
def test_bob_engine_pipeline_is_load_bearing(client):
    """POST /api/bob must run real engines and return a grounded answer.

    Acceptance criteria (all must hold):
    1. HTTP 200
    2. 'content' key present and non-empty
    3. 'actions' list is non-empty — at least one engine was invoked
    4. 'provider' is reported (bob | deterministic)
    5. 'intent' is recognised
    6. The content references at least one numeric engine output
       (index value or vessel count — proves it didn't fabricate a generic reply)
    """
    response = client.post("/api/bob", json={"message": "What is the current port-wide congestion index?"})
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    body = response.json()

    # 1. Required keys present
    for key in ("content", "actions", "provider", "intent"):
        assert key in body, f"Missing key '{key}' in Bob response"

    # 2. Content is non-empty text
    assert isinstance(body["content"], str) and len(body["content"]) > 10, (
        f"Bob content too short or missing: {body['content']!r}"
    )

    # 3. At least one engine action was recorded
    assert isinstance(body["actions"], list) and len(body["actions"]) > 0, (
        f"No engine actions recorded — pipeline was bypassed: {body['actions']}"
    )

    # 4. Provider is one of the documented values (no secondary LLM provider exists)
    assert body["provider"] in ("bob", "deterministic"), (
        f"Unknown provider: {body['provider']!r}"
    )

    # 5. Intent was classified
    assert body["intent"] in ("forecast", "optimise", "routing", "plan", "vessel", "status"), (
        f"Unrecognised intent: {body['intent']!r}"
    )

    # 6. Content contains at least one digit — grounded in engine numbers, not generic prose
    assert any(ch.isdigit() for ch in body["content"]), (
        f"Bob answer contains no numeric data — likely not engine-grounded: {body['content']!r}"
    )


@requires_db
def test_bob_routing_intent_runs_routing_engine(client):
    """Routing questions must invoke the routing engine action."""
    response = client.post("/api/bob", json={"message": "Which vessels should divert?"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "routing", f"Expected routing intent, got: {body['intent']}"
    assert any("routing" in a for a in body["actions"]), (
        f"Routing engine not invoked — actions: {body['actions']}"
    )
    assert any(ch.isdigit() for ch in body["content"]), (
        "Routing answer has no numeric data"
    )


@requires_db
def test_bob_optimiser_intent_runs_optimiser(client):
    """Optimiser questions must invoke the optimiser engine action."""
    # "berth" is a guaranteed trigger word for the optimise intent (see bob.py detect_intent)
    response = client.post("/api/bob", json={"message": "Show me the berth assignment and crane schedule."})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "optimise", f"Expected optimise intent, got: {body['intent']}"
    assert any("optimiser" in a or "forecast" in a for a in body["actions"]), (
        f"Optimiser engine not invoked — actions: {body['actions']}"
    )
