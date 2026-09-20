"""Bob — the engine-grounded operations assistant (shared brain).

Used by BOTH surfaces:
  * the dashboard via ``POST /api/bob`` (``routers/bob.py``)
  * IBM Bob via the MCP server (``app/mcp_server.py``)

Bob answers by ACTUALLY running the engines (forecast / optimiser / routing /
plan) and grounding the LLM strictly in their JSON output. If the LLM is
unavailable it returns a deterministic answer built from the same engine data,
so numbers are always engine-computed. ``actions`` records the tools executed.
"""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from ..models import ChatMessage
from . import llm, pipeline

INTENTS = ("plan", "optimise", "routing", "forecast", "vessel", "status")


def _known_tool_names() -> frozenset[str]:
    """MCP tool names the agent is expected to call (lazy import: mcp_server imports us)."""
    try:
        from ..mcp_server import mcp
        return frozenset(getattr(t, "name", None) for t in mcp._tool_manager.list_tools())
    except Exception:  # noqa: BLE001 — fall back to the documented tool registry
        return frozenset({"get_port_overview", "forecast_congestion", "rank_hotspots",
                          "detect_anomalies", "optimise_berth_cranes", "recommend_routing",
                          "generate_operations_plan", "simulate_scenario", "query_vessels",
                          "get_terminals", "get_data_provenance", "ask_operations_question"})


def agent_grounding_verdict(meta: dict) -> tuple[bool, str]:
    """Server-side verification of the PRIMARY agent path (brutal-audit finding).

    The system prompt asks Bob to fetch numbers through the PortFlow MCP tools, but a
    prompt enforces nothing. This gate enforces the one thing code CAN check: the agent
    must show tool-call evidence that it actually consulted the engines. An answer with
    zero tool calls (or only unknown tool names) cannot have touched engine data and is
    rejected — respond() then serves the deterministic engine-grounded fallback instead.

    Honest scope: this proves the engines were consulted; it does not re-verify every
    number in the free text. The response's ``grounded`` flag tells the client which
    guarantee applies (tool-evidenced agent vs engine-computed deterministic).
    """
    if int(meta.get("tool_calls") or 0) < 1:
        return False, "agent returned an answer with zero MCP tool calls"
    known = _known_tool_names()
    actions = meta.get("actions") or []
    # Stream tool names may be server-prefixed (mcp__portflow__rank_hotspots);
    # compare on the trailing tool name.
    bare = {a.split("__")[-1] for a in actions}
    if known and not (bare & known):
        return False, f"no recognised engine tool in actions {actions[:5]}"
    return True, f"tool-evidenced: {int(meta.get('tool_calls'))} tool call(s) via {actions[:3]}"


def detect_intent(message: str) -> str:
    m = message.lower()
    if re.search(r"\b(plan|shift|72|handover)\b", m):
        return "plan"
    if re.search(r"\b(optimi[sz]e|berth|crane|assignment)\b", m):
        return "optimise"
    if re.search(r"\b(rout|divert|slow|diversion)\b", m):
        return "routing"
    if re.search(r"\b(forecast|hotspot|predict|outlook|congestion)\b", m):
        return "forecast"
    if re.search(r"\b(vessel|queue|ship|anchor)\b", m):
        return "vessel"
    return "status"


def _counts(recs: list[dict]) -> dict:
    out: dict[str, int] = {}
    for r in recs:
        out[r["option"]] = out.get(r["option"], 0) + 1
    return out


def build_pack(full: dict, intent: str) -> tuple[dict, list[str]]:
    """Return (engine data pack, actions) for an intent, running the engines as needed."""
    if intent == "plan":
        return ({"summary": full["plan"]["summary"], "top_actions": full["plan"]["summary"]["top_actions"]},
                ["forecast.run", "optimiser.run", "routing.recommend", "plan.generate"])
    if intent == "optimise":
        return ({"metrics": full["optimiser"]["metrics"], "baseline": full["optimiser"]["baseline"],
                 "deltas": full["optimiser"]["deltas"], "solver": full["optimiser"]["solver"]},
                ["optimiser.run", "forecast.run"])
    if intent == "routing":
        return ({"top": full["routing"][:6], "counts": _counts(full["routing"])},
                ["routing.recommend", "forecast.run"])
    if intent == "forecast":
        port = full["forecasts"]["Z-PORT"]
        return ({"port": {"current": port.current, "peak": port.peak},
                 "hotspots": full["hotspots"]["ranked"][:4], "anomalies": full["anomalies"]},
                ["forecast.run", "hotspot.rank", "anomaly.detect"])
    if intent == "vessel":
        waiting = [v for v in full["ctx"].vessels if v.status != "INBOUND"]
        return ({"waiting": len(waiting),
                 "longest": sorted([{"name": v.name, "anchored_hours": v.anchored_hours,
                                     "carrier": v.carrier} for v in waiting],
                                   key=lambda x: -x["anchored_hours"])[:6]},
                ["vessels.query", "forecast.run"])
    overview = pipeline.build_overview(full["ctx"], full["forecasts"], full["hotspots"],
                                       full["anomalies"], full["optimiser"])
    return (overview["kpis"], ["overview.get"])


def deterministic_answer(intent: str, pack: dict) -> str:
    if intent == "forecast":
        p = pack["port"]
        hs = pack["hotspots"]
        top = hs[0] if hs else None
        s = (f"Port-wide index is {p['current']['index']}/100 now, forecast to peak at {p['peak']['index']} "
             f"around +{p['peak']['hour']}h. ")
        if top:
            s += (f"Top hotspot: {top['zone_name']} (risk {top['risk_score']}/100, binding resource "
                  f"{top['binding_constraint']}) — {top['explanation']}")
        return s
    if intent == "optimise":
        m = pack["metrics"]; b = pack["baseline"]; d = pack["deltas"]
        return (f"CP-SAT optimiser ({pack['solver']}) services {m['serviced']} vessels vs {b['serviced']} for FIFO; "
                f"weighted wait {m['weighted_wait_hours']}h vs {b['weighted_wait_hours']}h "
                f"(delta {d['weighted_wait']}h). Berth utilisation {m['berth_util_pct']}%, crane {m['crane_util_pct']}%.")
    if intent == "plan":
        sm = pack["summary"]
        return (f"72h plan: risk {sm['risk_level']}, {sm['total_arrivals']} arrivals, {sm['total_berthings']} berthings, "
                f"{sm['total_moves']:,} moves, peak index {sm['peak_index']} ({sm['peak_zone']}), "
                f"{sm['deferred_count']} deferred. " + " ".join(sm.get("top_actions", [])[:2]))
    if intent == "vessel":
        return (f"{pack['waiting']} vessels waiting; longest: "
                + ", ".join(f"{v['name']} ({v['anchored_hours']:.0f}h)" for v in pack.get("longest", [])[:3]))
    if intent == "routing":
        c = pack.get("counts", {})
        return ("Routing: " + ", ".join(f"{k}={v}" for k, v in c.items()) +
                ". See the Routing tab for divert / slow-steam / priority / hold detail.")
    k = pack
    return (f"Port index {k['port_index_now']}/100, peak {k['peak_forecast_index']} at +{k['peak_forecast_hour']}h; "
            f"{k['vessels_at_anchor']} at anchor, {k['vessels_inbound']} inbound, avg wait {k['avg_anchorage_wait']}h; "
            f"berth util {k['berth_util_pct']}%, crane util {k['crane_util_pct']}%.")


def _persist(db: Session, message: str, out: dict) -> None:
    db.add(ChatMessage(role="user", content=message, meta={"intent": out["intent"]}))
    db.add(ChatMessage(role="assistant", content=out["content"],
                       meta={"actions": out["actions"], "mode": out["mode"],
                             "provider": out["provider"], "intent": out["intent"],
                             "grounded": out.get("grounded", True),
                             "verification": out.get("verification")}))
    db.commit()


def respond(db: Session, message: str, persist: bool = True) -> dict:
    """Run the engines for the message's intent and return Bob's grounded answer."""
    intent = detect_intent(message)

    # ---- preferred: the REAL IBM Bob agent answers, fetching data via our MCP tools.
    # The answer is accepted ONLY if it passes the tool-evidence gate below; otherwise
    # we fall through to the deterministic engine-grounded path (numbers by construction).
    if llm.provider() == "bob":
        meta = llm.answer_meta(message)
        if meta["text"]:
            ok, verdict = agent_grounding_verdict(meta)
            if ok:
                out = {"content": meta["text"], "actions": meta["actions"] or ["bob.agent"],
                       "mode": "llm", "provider": "bob", "intent": intent, "grounded": True,
                       "verification": verdict,
                       "tool_calls": meta.get("tool_calls", 0), "cost_usd": meta.get("cost_usd", 0.0),
                       "engine_data": None}
                if persist:
                    _persist(db, message, out)
                return out
            print(f"[bob] agent answer rejected by grounding gate ({verdict}) — engine fallback")
        print("[bob] IBM Bob agent unavailable/failed - using the local engine pack")

    # ---- fallback: run the engines locally and ground the LLM in their JSON
    full = pipeline.build_full(db, persist=False)
    pack, actions = build_pack(full, intent)
    meta = llm.answer_meta(message, json.dumps(pack, default=str))
    if not meta["text"]:
        meta = {"text": deterministic_answer(intent, pack), "provider": "deterministic",
                "actions": actions, "tool_calls": 0, "cost_usd": 0.0}
    out = {"content": meta["text"], "actions": meta["actions"] or actions,
           "mode": "llm" if meta["provider"] != "deterministic" else "deterministic",
           "provider": meta["provider"], "intent": intent, "grounded": True,
           "verification": "engine-computed: numbers built from the same engine pack the UI reads",
           "engine_data": pack}
    if persist:
        _persist(db, message, out)
    return out


__all__ = ["detect_intent", "build_pack", "deterministic_answer", "agent_grounding_verdict",
           "respond", "INTENTS"]
