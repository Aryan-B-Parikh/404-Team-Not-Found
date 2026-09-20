"""Narrative layer — **IBM Bob first**, with deterministic engine-grounded fallback.

Provider resolution (``LLM_PROVIDER=auto|bob|deterministic``):
  * ``bob``   — the real IBM Bob agent (``services/bob_agent.py``); Bob fetches
                operational numbers through our MCP server.
  * ``deterministic`` — a transparent template over the same engine numbers.

There is intentionally **no secondary external LLM fallback**. This keeps IBM Bob
load-bearing and makes the provenance story unambiguous for the hackathon demo.
"""

from __future__ import annotations

from ..config import get_settings
from . import bob_agent


# ------------------------------------------------------------------ provider
def _resolve(setting: str, has_bob: bool) -> str:
    """Pure provider-resolution rule: Bob when available, otherwise deterministic."""
    if setting in ("bob", "deterministic"):
        return setting
    return "bob" if has_bob else "deterministic"


def provider() -> str:
    s = get_settings()
    return _resolve(s.llm_provider, bob_agent.available())


def is_enabled() -> bool:
    return provider() == "bob"


# ------------------------------------------------------------------ public API
def answer_meta(question: str, engine_data: str = "", history: list[dict] | None = None) -> dict:
    """Grounded Q&A. Returns {text, provider, actions, tool_calls, cost_usd}.

    ``engine_data`` and ``history`` remain accepted for API compatibility, but
    IBM Bob obtains live data through MCP when available. If Bob is unavailable,
    the caller uses the deterministic engine-grounded path.
    """
    if provider() != "bob":
        return {"text": "", "provider": "deterministic", "actions": [], "tool_calls": 0, "cost_usd": 0.0}

    try:
        r = bob_agent.run(question)
    except Exception as exc:  # noqa: BLE001
        r = {"ok": False, "status": "exception", "error": str(exc),
             "actions": [], "tool_calls": 0, "cost": 0.0}
    if r["ok"]:
        return {"text": r["text"], "provider": "bob", "actions": r["actions"],
                "tool_calls": r["tool_calls"], "cost_usd": r["cost"]}
    print(f"[llm] Bob agent failed ({r.get('status')}: {r.get('error')}) — deterministic fallback")
    return {"text": "", "provider": "deterministic", "actions": [], "tool_calls": 0, "cost_usd": 0.0}


def answer(question: str, engine_data: str, history: list[dict] | None = None) -> tuple[str, str]:
    """Back-compat wrapper → (text, provider)."""
    meta = answer_meta(question, engine_data, history)
    return meta["text"], meta["provider"]


def narrate_meta(text_plan: str, summary: dict) -> dict:
    """72h plan briefing. Bob is the only LLM provider; otherwise use deterministic text."""
    if provider() == "bob":
        prompt = (
            "Rewrite the following validated 72-hour port operations plan as a concise shift-supervisor "
            "briefing (max 220 words). Use ONLY the numbers present; never invent figures.\n\n"
            f"PLAN:\n{text_plan[:6000]}"
        )
        try:
            r = bob_agent.run(prompt, max_turns=1)
        except Exception as exc:  # noqa: BLE001
            r = {"ok": False, "status": "exception", "error": str(exc),
                 "actions": [], "tool_calls": 0, "cost": 0.0}
        if r["ok"]:
            return {"text": r["text"], "provider": "bob", "actions": r["actions"],
                    "tool_calls": r["tool_calls"], "cost_usd": r["cost"]}
        print(f"[llm] Bob narrate failed ({r.get('status')}: {r.get('error')}) — deterministic fallback")

    return {"text": _deterministic(summary), "provider": "deterministic", "actions": [],
            "tool_calls": 0, "cost_usd": 0.0}


def narrate(text_plan: str, summary: dict) -> tuple[str, str]:
    """Back-compat wrapper → (text, provider)."""
    meta = narrate_meta(text_plan, summary)
    return meta["text"], meta["provider"]


def _deterministic(summary: dict) -> str:
    return (
        f"SHIFT BRIEFING — risk {summary['risk_level']}. "
        f"{summary['total_arrivals']} arrivals and {summary['total_berthings']} berthings across 12 shifts; "
        f"{summary['total_moves']:,} moves and {summary['crane_hours']:,} crane-hours planned. "
        f"Port-wide peak index {summary['peak_index']} ({summary['peak_zone']}); "
        f"{summary['deferred_count']} vessel(s) deferred to the routing engine; "
        f"idle berth-hours {summary['idle_berth_hours_pct']}%. "
        + " ".join(summary.get("top_actions", [])[:2])
    )
