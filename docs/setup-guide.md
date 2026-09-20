# Setup Guide — PortPulse AI

Tested stack: **Python 3.11 (uv) + FastAPI + PostgreSQL + React/Vite**.

## 1. Prerequisites

- **uv** for the Python toolchain
- **PostgreSQL** running locally
- **Node.js ≥ 20** + npm
- **IBM Bob CLI** for the load-bearing agentic assistant; optional when running the deterministic fallback

## 2. Run locally

```bash
git clone https://github.com/Aryan-B-Parikh/404-Team-Not-Found.git
cd 404-Team-Not-Found

# Create the PostgreSQL database once
createdb -U postgres portflow

# Backend
cd src/backend
uv sync --python 3.11
cp .env.example .env
# Set DATABASE_URL. Set BOB_API_KEY if IBM Bob agent mode is available.
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000

# Frontend — second terminal
cd ../frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 3. IBM Bob integration

The project includes a portable project-level Bob configuration at `.bob/mcp.json`. Open the repository as a workspace in IBM Bob; Bob can discover the PortPulse MCP server from that configuration.

The MCP server is also runnable directly:

```bash
cd src/backend
uv run python -m app.mcp_server
```

Bob is the agent/orchestrator. It selects MCP tools, executes the underlying forecasting, anomaly, hotspot, optimisation, routing, scenario and planning engines, then synthesizes their structured results. There is no secondary external LLM provider. If Bob is unavailable, the application uses a deterministic briefing over the same engine outputs.

## 4. Data sources and provenance

| Source | Role | Status |
|---|---|---|
| Port of Long Beach fact sheets | Real berth/crane/terminal capacity | Active |
| DEMO_AIS / SimPy | Synthetic, reproducible vessel/congestion history | Active offline demo path |
| NOAA AccessAIS | Real AIS history import path | Available |
| Open-Meteo | Weather features | Active when available |
| BTS PPFSP parser | Benchmark/validation path | Available |

The default offline history is explicitly labelled `DEMO_AIS`; it is not measured AIS. A real NOAA AccessAIS CSV imported through `/api/ais/import` is labelled `AIS`.

## 5. Core API

- `/api/overview` — command view
- `/api/forecast?zone=` — LightGBM 72h forecast + uncertainty
- `/api/optimise` — OR-Tools CP-SAT BAP/QCAP
- `/api/routing` — routing recommendations
- `/api/plan` — persisted/provenance-aware 72h plan
- `/api/terminals` — real POLB capacity + live state
- `/api/vessels` — vessel queue + assignments
- `/api/vessels/upload` — CSV schedule ingestion + ETA revision history + auto-replan
- `/api/anomalies` — Isolation Forest disruption flags
- `/api/hotspots` — binding-resource risk ranking
- `/api/quality` — data completeness + normalization status
- `/api/weather` — Open-Meteo observations
- `/api/scenarios` — what-if stress tests
- `/api/bob` — IBM Bob operational assistant
- `/api/bob/status` — Bob CLI/configuration status
- MCP `app.mcp_server` — 12 Bob tools + resources + prompts

## 6. Performance limitation

The prototype prioritizes reproducibility and explainability over production dispatch latency. Cold LightGBM forecasting is approximately **11 seconds** and a cold full plan can take approximately **20–30 seconds**; warm process-cached requests are substantially faster. For the live walkthrough, prewarm the engines before the Bob interaction.

## 7. Verification

```bash
cd src/backend
uv run python -m pytest -q
```

Then verify `http://localhost:8000/health` returns `{"status":"ok"}` and open the frontend. In Bob, ask:

> What is the biggest operational risk over the next 72 hours?

A valid Bob run should show MCP tool actions in the Bob response metadata.

## 8. Demo scope

The project focuses on the core decision loop: **observe → predict → explain risk → stress-test → optimise → route → plan → Bob**. Full live TOS/EDI integration, continuous retraining, port-wide coverage and enterprise deployment are Phase-2 items.
