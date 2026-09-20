---
name: port-operations-response
description: Analyze San Pedro Bay congestion, disruptions, berth/crane constraints, routing decisions, and shift actions using PortFlow SBX MCP tools.
---

When the user asks for an operational decision:

1. Establish the current state with `get_port_overview` when broad context is needed.
2. Use the smallest set of MCP tools that can prove the answer.
3. For congestion, use `forecast_congestion`; for bottlenecks use `rank_hotspots`; for anomalies use `detect_anomalies`.
4. For berth/crane decisions use `optimise_berth_cranes`; always compare with FIFO when available.
5. For disruptions or what-if requests use `simulate_scenario`, then regenerate or inspect the affected 72-hour plan.
6. For vessel actions use `query_vessels` and `recommend_routing`.
7. For shift handover use `generate_operations_plan` and summarize only the next actionable shift first.
8. Use `get_data_provenance` whenever the user asks whether the data is real, synthetic, current, or trustworthy.
9. Structure the answer as:
   - Situation
   - Evidence from tools
   - Decision
   - Expected impact
   - Caveat/provenance when relevant
10. Never invent a metric, vessel state, ETA, savings value, or confidence value.
