"""IBM Bob stream-json parser + grounding gate + retry policy — pure unit tests."""

from __future__ import annotations

from app.services import bob_agent
from app.services.bob import agent_grounding_verdict
from app.services.bob_agent import parse_stream

# Shape captured from a real `bob run --format stream-json` session.
STREAM = "\n".join([
    '{"type":"message","role":"user","content":"call the tool"}',
    '{"type":"tool_use","tool_name":"mcp__portflow__rank_hotspots","parameters":{}}',
    '{"type":"tool_result","tool_id":"x","status":"success","output":"{\\"ranked\\":[]}"}',
    '{"type":"message","role":"assistant","content":"**Zone:** "}',
    '{"type":"message","role":"assistant","content":"`Z-LBCT`"}',
    '{"type":"message","role":"assistant","content":"\\n**Risk:** 38.0"}',
    '{"type":"result","status":"success","stats":{"tool_calls":1,"session_costs":0.0542}}',
])

JSON_FORMAT = '{"type":"result","status":"success","stats":{"tool_calls":0,"session_costs":0.02},"last_message":"PORTPULSE-OK"}'


def test_accumulates_assistant_deltas_and_tool_names():
    r = parse_stream(STREAM)
    assert r["status"] == "success"
    assert r["text"] == "**Zone:** `Z-LBCT`\n**Risk:** 38.0"      # user message excluded
    assert r["actions"] == ["mcp__portflow__rank_hotspots"]
    assert r["tool_calls"] == 1
    assert round(r["cost"], 4) == 0.0542


def test_last_message_wins_when_present():
    r = parse_stream(JSON_FORMAT)
    assert r["text"] == "PORTPULSE-OK"
    assert r["actions"] == []


def test_garbage_and_partial_lines_are_ignored():
    r = parse_stream("not json\n{broken\n" + STREAM)
    assert r["text"].startswith("**Zone:**")
    assert parse_stream("")["text"] == ""


def test_failed_status_is_reported():
    r = parse_stream('{"type":"result","status":"error","stats":{"tool_calls":0,"session_costs":0}}')
    assert r["status"] == "error"
    assert r["text"] == ""


# ------------------------------------------------- grounding gate (brutal audit)
def _agent_meta(tool_calls=1, actions=None):
    return {"text": "Port index is 100/100.", "actions": actions or ["mcp__portflow__rank_hotspots"],
            "tool_calls": tool_calls}


def test_gate_accepts_tool_evidenced_answer():
    ok, why = agent_grounding_verdict(_agent_meta())
    assert ok and "tool-evidenced" in why


def test_gate_rejects_answer_without_tool_calls():
    """An operational answer with zero MCP tool calls cannot have touched engine data."""
    ok, why = agent_grounding_verdict(_agent_meta(tool_calls=0, actions=[]))
    assert not ok and "zero MCP tool calls" in why


def test_gate_rejects_unknown_tools_even_with_call_count():
    ok, why = agent_grounding_verdict(_agent_meta(actions=["run_terminal", "web_search"]))
    assert not ok and "no recognised engine tool" in why


def test_gate_matches_server_prefixed_tool_names():
    ok, why = agent_grounding_verdict(_agent_meta(actions=["mcp__portflow__forecast_congestion"]))
    assert ok


# ------------------------------------------------------------------ retry policy
def test_run_retries_only_transient_timeouts(monkeypatch):
    calls = []

    def fake_run_once(prompt, *, max_turns=None, timeout=None):
        calls.append(prompt)
        return {"ok": False, "text": "", "actions": [], "tool_calls": 0,
                "status": "timeout", "error": "bob timeout", "cost": 0.0}

    monkeypatch.setattr(bob_agent, "_run_once", fake_run_once)
    r = bob_agent.run("q", retries=1)
    assert len(calls) == 2          # timeout is transient -> retried once
    assert r["status"] == "timeout"


def test_run_fails_fast_on_deterministic_failure(monkeypatch):
    """A malformed prompt / missing CLI fails the same way every time — retrying it
    just repeats the failure. Only timeouts earn a second attempt."""
    calls = []

    def fake_run_once(prompt, *, max_turns=None, timeout=None):
        calls.append(prompt)
        return {"ok": False, "text": "", "actions": [], "tool_calls": 0,
                "status": "error", "error": "bad prompt", "cost": 0.0}

    monkeypatch.setattr(bob_agent, "_run_once", fake_run_once)
    r = bob_agent.run("q", retries=1)
    assert len(calls) == 1          # non-timeout -> fail fast
    assert r["status"] == "error"
