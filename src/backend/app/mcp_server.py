"""PortPulse AI — MCP server for IBM Bob.

Exposes the operational engines as Model Context Protocol tools so IBM Bob can
actually execute forecasts, anomaly detection, hotspot ranking, CP-SAT berth /
crane optimisation, routing, scenarios, and 72-hour planning.
"""

from __future__ import annotations

import argparse
import json

from mcp.server.mcpserver import MCPServer

from . import reference as ref
from .db import SessionLocal
from .serialize import forecast_to_dict, vessel_to_dict
from .services import bob as bob_svc
from .services import pipeline

mcp = MCPServer(
    name="PortPulse AI", version="0.1.0",
    instructions=(
        "PortPulse AI San Pedro Bay operations decision support. Tools return engine-computed numbers. "
        "For operational questions, use tools before answering and never invent figures. "
        "Use forecast_congestion for outlooks, rank_hotspots/detect_anomalies for risk explanation, "
        "optimise_berth_cranes for CP-SAT vs FIFO decisions, simulate_scenario for what-if changes, "
        "recommend_routing/query_vessels for vessel actions, and generate_operations_plan for shift plans. "
        "Terminal capacity is real Port of Long Beach reference data. DEMO_AIS is synthetic demo history; "
        "AIS is real imported NOAA AccessAIS history. State provenance when relevant."
    ),
)


def _full(db, persist=False):
    return pipeline.build_full(db, persist=persist)


def _session():
    return SessionLocal()


@mcp.tool(description="Live port overview: current KPIs, 72h congestion, hotspot risk, anomalies, arrivals and utilisation. Call this for broad situational awareness.")
def get_port_overview() -> dict:
    db = _session()
    try:
        f = _full(db, persist=False)
        return pipeline.build_overview(f["ctx"], f["forecasts"], f["hotspots"], f["anomalies"], f["optimiser"])
    finally:
        db.close()


@mcp.tool(description="72-hour LightGBM congestion forecast for a zone. Returns hourly index, queue, wait, yard utilisation, uncertainty bands, validation, drivers and confidence. Valid zones: Z-PORT, Z-LBCT, Z-ITS, Z-PCT, Z-TTI.")
def forecast_congestion(zone: str = "Z-PORT") -> dict:
    if zone not in ref.ALL_ZONES:
        return {"error": f"unknown zone {zone}", "valid_zones": ref.ALL_ZONES}
    db = _session()
    try:
        f = _full(db, persist=False)
        return {
            "zone": zone,
            "forecast": forecast_to_dict(f["forecasts"][zone]),
            "summary_all_zones": {
                z: {
                    "current_index": fc.current["index"],
                    "peak_index": fc.peak["index"],
                    "peak_hour": fc.peak["hour"],
                }
                for z, fc in f["forecasts"].items()
            },
        }
    finally:
        db.close()


@mcp.tool(description="Rank congestion hotspots using the composite risk engine and report the binding resource: BERTH, CRANE, YARD or GATE, with confidence and explanation.")
def rank_hotspots() -> dict:
    db = _session()
    try:
        return _full(db, persist=False)["hotspots"]
    finally:
        db.close()


@mcp.tool(description="Detect operational anomalies with Isolation Forest and classify them as bunching, outage, yard saturation, weather or data error.")
def detect_anomalies() -> dict:
    db = _session()
    try:
        f = _full(db, persist=False)
        return {"anomalies": f["anomalies"], "method": "scikit-learn IsolationForest"}
    finally:
        db.close()


@mcp.tool(description="Run the real OR-Tools CP-SAT berth allocation and quay-crane assignment under physical constraints and compare it with FIFO. Use crane_factor and move_rate_per_crane_hour for capacity/productivity what-if analysis.")
def optimise_berth_cranes(crane_factor: float = 1.0, move_rate_per_crane_hour: float = 28.0) -> dict:
    db = _session()
    try:
        f = _full(db, persist=False)
        out = pipeline.run_optimiser(
            f["ctx"],
            f["forecasts"],
            {
                "crane_factor": max(0.5, min(1.0, crane_factor)),
                "move_rate_per_crane_hour": max(20.0, min(35.0, move_rate_per_crane_hour)),
            },
        )
        return {
            k: out[k]
            for k in (
                "solver", "status", "objective", "solve_ms", "params", "metrics",
                "baseline", "deltas", "weights", "assignments", "deferred",
            )
        }
    finally:
        db.close()


@mcp.tool(description="Recommend vessel actions: DIVERT, SLOW_STEAM, PRIORITY_WINDOW or HOLD. Returns predicted wait, sustained-congestion evidence, estimated savings, confidence and rationale.")
def recommend_routing() -> dict:
    db = _session()
    try:
        recs = _full(db, persist=False)["routing"]
        counts = {}
        for r in recs:
            counts[r["option"]] = counts.get(r["option"], 0) + 1
        return {
            "recommendations": recs,
            "counts": counts,
            "total_savings_usd": sum(r["est_savings_usd"] for r in recs),
        }
    finally:
        db.close()


@mcp.tool(description="Generate the 72-hour operations plan as 12 six-hour shifts with arrivals, berthings, crane deployment, alerts, routing deadlines and supervisor checklist. Set include_text=true for printable text.")
def generate_operations_plan(include_text: bool = False) -> dict:
    db = _session()
    try:
        plan = _full(db, persist=False)["plan"]
        out = {"summary": plan["summary"], "shifts": plan["shifts"]}
        if include_text:
            out["text"] = plan["text"]
        return out
    finally:
        db.close()


@mcp.tool(description="Run a what-if scenario through the real CP-SAT engine. Compare baseline vs impaired crane availability/productivity and return the impact on serviced vessels, moves, wait and makespan.")
def simulate_scenario(crane_factor: float = 0.75, move_rate_per_crane_hour: float = 24.0) -> dict:
    db = _session()
    try:
        f = _full(db, persist=False)
        base = pipeline.run_optimiser(f["ctx"], f["forecasts"], {})
        scen = pipeline.run_optimiser(
            f["ctx"],
            f["forecasts"],
            {
                "crane_factor": max(0.5, min(1.0, crane_factor)),
                "move_rate_per_crane_hour": max(20.0, min(35.0, move_rate_per_crane_hour)),
            },
        )
        return {
            "params": scen["params"],
            "baseline": base["metrics"],
            "scenario": scen["metrics"],
            "impact": {
                "serviced": scen["metrics"]["serviced"] - base["metrics"]["serviced"],
                "moves": scen["metrics"]["total_moves"] - base["metrics"]["total_moves"],
                "avg_wait": round(scen["metrics"]["avg_wait_hours"] - base["metrics"]["avg_wait_hours"], 1),
                "makespan": round(scen["metrics"]["makespan_hours"] - base["metrics"]["makespan_hours"], 1),
            },
        }
    finally:
        db.close()


@mcp.tool(description="Query the current vessel queue, optionally filtered by status, and include the current CP-SAT assignment.")
def query_vessels(status: str | None = None) -> dict:
    db = _session()
    try:
        f = _full(db, persist=False)
        assignment = {a["vessel_id"]: a for a in f["optimiser"]["assignments"]}
        rows = []
        for v in f["ctx"].vessels:
            if status and v.status.upper() != status.upper():
                continue
            d = vessel_to_dict(v)
            a = assignment.get(v.id)
            d["assignment"] = (
                {
                    "berth_name": a["berth_name"],
                    "terminal_code": a["terminal_code"],
                    "start_hour": a["start_hour"],
                    "cranes": a["cranes"],
                }
                if a
                else None
            )
            rows.append(d)
        return {"count": len(rows), "vessels": rows}
    finally:
        db.close()


@mcp.tool(description="Return Port of Long Beach reference terminal capacity plus live crane availability, yard utilisation and gate queue. Capacity figures are real reference data; live operational state follows dataset provenance.")
def get_terminals() -> dict:
    db = _session()
    try:
        f = _full(db, persist=False)
        return {
            "source": "Port of Long Beach terminal fact sheets for capacity; live yard/gate state from current dataset",
            "terminals": [
                {
                    "code": t.code,
                    "name": t.name,
                    "pier": t.pier,
                    "berth_length_ft": t.berth_length_ft,
                    "deepsea_berths": t.deepsea_berths,
                    "gantry_cranes": t.gantry_cranes,
                    "capacity_teu_m": t.capacity_teu_m,
                    "zone_code": t.zone_code,
                    "note": t.note,
                    "available_cranes": f["ctx"].cranes.get(t.code),
                    "yard_util_pct": f["ctx"].yard_util.get(t.code),
                    "gate_queue": f["ctx"].gate_queue.get(t.code),
                }
                for t in f["ctx"].terminals
            ],
        }
    finally:
        db.close()


@mcp.tool(description="Return explicit data provenance and model state: AIS vs DEMO_AIS, context fingerprint, weather usage, forecast model version and confidence. Use this when a user asks whether data is real.")
def get_data_provenance() -> dict:
    db = _session()
    try:
        f = _full(db, persist=False)
        port = f["forecasts"]["Z-PORT"]
        return {
            "dataset_source": f["ctx"].dataset_source,
            "data_version": f["ctx"].data_version,
            "dataset_note": pipeline.DATASET_NOTE,
            "weather_used": bool(port.weather_used),
            "weather_source": "Open-Meteo" if port.weather_used else None,
            "model_version": port.model.get("model_version"),
            "confidence": port.confidence,
        }
    finally:
        db.close()


@mcp.tool(description="Ask Bob an operational question. This is a helper for nested MCP workflows; it remains engine-grounded and returns the detected intent, actions and provider mode.")
def ask_operations_question(question: str) -> dict:
    db = _session()
    try:
        out = bob_svc.respond(db, question, persist=False)
        return {"answer": out["content"], "intent": out["intent"], "actions": out["actions"], "mode": out["mode"]}
    finally:
        db.close()


@mcp.resource("portflow://overview", name="Port overview", mime_type="application/json", description="Live KPIs, zone congestion, hotspot risk and anomalies.")
def res_overview() -> str:
    db = _session()
    try:
        return json.dumps(
            pipeline.build_overview(
                *(_full(db, persist=False)[k] for k in ("ctx", "forecasts", "hotspots", "anomalies", "optimiser"))
            ),
            default=str,
        )
    finally:
        db.close()


@mcp.resource("portflow://terminals", name="Terminal capacity", mime_type="application/json", description="POLB capacity plus live state.")
def res_terminals() -> str:
    return json.dumps(get_terminals(), default=str)


@mcp.resource("portflow://plan", name="72h operations plan", mime_type="text/plain", description="Printable 72-hour operations plan.")
def res_plan() -> str:
    db = _session()
    try:
        return _full(db, persist=False)["plan"]["text"]
    finally:
        db.close()


@mcp.resource("portflow://forecast/{zone}", name="Zone forecast", mime_type="application/json", description="72h forecast for a PortPulse zone.")
def res_forecast(zone: str) -> str:
    db = _session()
    try:
        f = _full(db, persist=False)
        return (
            json.dumps(f["forecasts"][zone], default=str)
            if zone in f["forecasts"]
            else json.dumps({"error": f"unknown zone {zone}", "valid": ref.ALL_ZONES})
        )
    finally:
        db.close()


@mcp.prompt(description="Shift-handover briefing grounded in the current 72h plan and port overview.")
def shift_handover_briefing() -> str:
    return "Call generate_operations_plan(include_text=true), get_port_overview and get_data_provenance. Write a concise supervisor handover with risk, arrivals, berthings, binding constraints, decide-by actions and checklist. Use only returned numbers and state provenance."


@mcp.prompt(description="Diversion decision for a vessel or affected queue.")
def diversion_decision(vessel: str = "") -> str:
    return f"Call recommend_routing and forecast_congestion; {('also call query_vessels for ' + vessel + '.') if vessel else 'call query_vessels if a specific vessel is relevant.'} Explain wait, sustained-congestion evidence, savings, confidence and trade-offs using only tool results."


@mcp.prompt(description="Incident response workflow for a disruption or capacity loss.")
def disruption_response(crane_factor: float = 0.75) -> str:
    return f"Call get_port_overview, forecast_congestion, rank_hotspots, simulate_scenario(crane_factor={crane_factor}) and generate_operations_plan. Explain the causal chain and finish with the three most urgent actions. Never invent a number."


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="app.mcp_server", description="PortPulse AI MCP server for IBM Bob")
    p.add_argument("--http", nargs="?", const=8765, type=int, default=None)
    args = p.parse_args(argv)
    mcp.run(
        transport="stdio" if args.http is None else "streamable-http",
        **({} if args.http is None else {"host": "127.0.0.1", "port": args.http}),
    )


if __name__ == "__main__":
    main()
