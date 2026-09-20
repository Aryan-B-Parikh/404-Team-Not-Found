# IBM Bob integration — MCP server

**PortPulse AI** exposes its operational engines to **IBM Bob** through a Model Context Protocol (MCP) server (`src/backend/app/mcp_server.py`). Bob is the load-bearing agent; the application has no secondary external LLM provider.

## 1. Two directions

- **Bob → engines:** IBM Bob discovers and calls the MCP tools. The tools execute LightGBM forecasting, Isolation Forest anomaly detection, risk scoring, OR-Tools CP-SAT optimisation, routing, scenarios and plan generation.
- **App → Bob:** the dashboard's Bob AI surface invokes the real Bob agent, which uses the same MCP tools.

If Bob is unavailable, the application falls back only to a transparent deterministic briefing generated from engine output.

## 2. Run the MCP server

```bash
cd src/backend
uv sync --python 3.11
uv run python -m app.mcp_server
```

## 3. Register with IBM Bob

The repository includes a portable project-level `.bob/mcp.json`. Open the repository as a Bob workspace and use the project configuration. The equivalent STDIO registration is:

```json
{
  "mcpServers": {
    "portpulse": {
      "command": "uv",
      "args": ["run", "--directory", "<ABSOLUTE-PATH-TO-REPO>/src/backend", "python", "-m", "app.mcp_server"]
    }
  }
}
```

Bob then discovers the operational tools automatically.

## 4. Tools

| Tool | Engine / purpose |
|---|---|
| `get_port_overview` | KPIs, forecasts, hotspots, anomalies and optimisation state |
| `forecast_congestion(zone)` | LightGBM 72h forecast + uncertainty |
| `rank_hotspots` | composite risk + binding resource |
| `detect_anomalies` | Isolation Forest disruption flags |
| `optimise_berth_cranes(...)` | OR-Tools CP-SAT BAP/QCAP + FIFO comparison |
| `recommend_routing` | routing decision engine |
| `generate_operations_plan(...)` | 12-shift / 72h plan |
| `simulate_scenario(...)` | baseline vs stress scenario |
| `query_vessels(status)` | vessel queue + assignments |
| `get_terminals` | POLB capacity + operational state |
| `get_data_provenance` | real/synthetic source and model provenance |
| `ask_operations_question(question)` | grounded operational assistant helper |

**Total: 12 MCP tools, 4 resources and 3 prompts.**

## 5. Architecture principle

```text
Operational data
      ↓
LightGBM + Isolation Forest
      ↓
Risk / hotspot attribution
      ↓
OR-Tools CP-SAT
      ↓
Routing + 72h plan
      ↓
IBM Bob via MCP
      ↓
Supervisor-facing explanation
```

**Bob does not create the berth schedule.** The constrained optimizer creates the schedule. Bob chooses the relevant tools, reasons over their outputs and communicates the operational decision.

## 6. Provenance

- `DEMO_AIS` = synthetic, reproducible offline demonstration history; not measured AIS.
- `AIS` = real NOAA AccessAIS history imported through the dedicated import path.
- POLB terminal/berth/crane/yard/gate capacity = reference data used as operational constraints.

MCP instructions require Bob to state provenance when it materially affects an answer and never invent operational numbers.

## 7. Verification

```bash
cd src/backend
uv run python -m pytest -q
```

For the strongest Bob verification, ask:

> Assume we lose 25% of crane capacity. What changes, why, and what should the supervisor do next shift?

A successful run should invoke scenario/optimisation/plan tools and expose the tool actions in the application response metadata.

## 8. Deterministic fallback

The deterministic fallback is an availability mechanism, not another AI provider. It uses the same engine outputs and cannot create a new schedule or operational number.
