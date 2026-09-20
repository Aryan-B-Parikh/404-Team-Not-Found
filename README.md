# 🚀 PortPulse AI — Container Congestion Predictor & Port Operations Optimiser

> A 72-hour port-operations cockpit for San Pedro Bay (Ports of Long Beach / Los Angeles), using FastAPI · LightGBM · OR-Tools CP-SAT · SimPy · PostgreSQL · React/Vite and **IBM Bob via MCP** as the load-bearing agentic layer.

---

## 👥 Team

| Field | Value |
|---|---|
| **Team** | 404-Team-Not-Found |
| **Team Lead** | Aryan Parikh — aryan81006@gmail.com |
| **Members** | Mahima Kukadiya (kukadiyamahimace@gmail.com) |

---

## 🎯 Problem Statement

San Pedro Bay — the twin Ports of Long Beach and Los Angeles — needs coordinated visibility across vessel arrivals, berth/crane capacity, yard pressure and congestion. During the 2021 backlog, reactive hotspot discovery, manual berth planning and late routing decisions demonstrated the cost of acting after queues had already formed.

Full analysis and scope: [`docs/problem-statement.md`](docs/problem-statement.md).

---

## 💡 Solution

PortPulse AI forecasts congestion **before** it happens and gives a shift supervisor a physically constrained 72-hour operating plan.

A **SimPy** discrete-event simulation generates a reproducible synthetic operations layer over the **REAL** Port of Long Beach terminal-capacity table. **LightGBM** forecasts congestion with quantile uncertainty bands (validated via a 48-hour holdout and multi-origin rollouts; MAE/R²/skill-vs-persistence are reported per run). **Isolation Forest** detects disruptions. A composite risk score identifies the **binding resource**. **OR-Tools CP-SAT** performs berth allocation + quay-crane assignment under hard physical constraints and is contrasted with a FIFO baseline. A FastAPI gateway serves the engines to the React/Vite dashboard and to **IBM Bob**, which orchestrates the engines through MCP and produces the operational explanation.

### The four capability pillars — and where each lives

| # | Capability | Engine code | API route | UI tab |
|---|---|---|---|---|
| 1 | Predict congestion hotspots | `services/forecasting.py` + `hotspot.py` | `GET /api/forecast?zone=…` | **Forecast** |
| 2 | Recommend alternate routing | `services/routing.py` | `GET /api/routing` | **Routing** |
| 3 | Optimise berth & crane assignments | `services/optimiser.py` | `GET`/`POST /api/optimise` | **Berth & Cranes** |
| 4 | 72-hour operations plan | `services/plan.py` | `GET`/`POST /api/plan` | **72-Hr Plan** |

Cross-cutting: KPIs / hotspots / anomalies via `pipeline.py` → `GET /api/overview`; Bob via `services/bob_agent.py` → `GET`/`POST /api/bob`.

### 🤖 IBM Bob integration — load-bearing in **both** directions

| Direction | Flow |
|---|---|
| **Bob → engines** | IBM Bob acts as the MCP client and calls the PortPulse MCP server (`src/backend/app/mcp_server.py`), which exposes **12 operational tools**, 4 resources and 3 prompts. The tools execute the actual forecasting, anomaly, hotspot, optimisation, routing, scenario, vessel and planning engines. |
| **App → Bob** | The dashboard's Bob AI surface invokes the real IBM Bob agent (`services/bob_agent.py`). Bob obtains operational evidence through the same MCP tools and returns tool-call metadata. |

Bob is therefore the **agent/orchestrator**, not a decorative chat layer. If Bob is unavailable, the application uses a transparent deterministic briefing over the same engine outputs; there is no secondary external LLM provider.

Setup + registration: [`docs/bob-mcp.md`](docs/bob-mcp.md).

---

## ✨ Key Features

- **SimPy operations layer** — reproducible vessel calls, ETA-revision history and hourly congestion observations.
- **LightGBM forecasting with quantile bands** — point + 0.1/0.9 regression per zone over 24/48/72 h, with validation and persistence-skill reporting.
- **OR-Tools CP-SAT optimiser (BAP/QCAP)** — berth assignment, crane count and start time under berth length/depth, crane reach, overlap and terminal crane-pool constraints; FIFO baseline included.
- **Isolation Forest anomaly detection** — identifies operational disruption patterns and possible data errors.
- **Resource-binding hotspot scoring** — combines queue, utilisation, variance, uncertainty and disruption signals to identify the binding resource.
- **IBM Bob load-bearing agent** — Bob uses the MCP tools to retrieve engine-computed evidence, reason across multiple operational steps, and produce an auditable supervisor-facing decision.
- **Operational extras** — what-if scenario simulator (crane outage, productivity shock, berth add/remove, vessel bunching, schedule shift, rollback), real POLB reference capacity table, CSV exports, weather features and dynamic data-provenance reporting.
- **Routing economics, labelled** — `est_savings_usd` figures are indicative planning estimates from linear formulas over public mid-range references; the formulas and their basis are exposed at `GET /api/routing` (`cost_model`), and external-port diversion requires an operator-supplied live port-status feed (`PORT_STATUS_JSON`).

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python 3.11, TypeScript |
| **Frameworks** | FastAPI, React, Vite, Tailwind CSS, SQLAlchemy 2, LightGBM, scikit-learn, Google OR-Tools (CP-SAT), SimPy |
| **AI agent layer** | IBM Bob, Model Context Protocol (MCP) — Bob is the only LLM narrative provider; a deterministic template over the same engine numbers is used when the Bob agent is unavailable |
| **Databases** | PostgreSQL (psycopg3) |
| **Other** | Recharts, uv, NOAA AccessAIS import pipeline, Open-Meteo |

---

## 📁 Repository Structure

```text
portpulse-ai/
├── src/                          # All project code
│   ├── backend/                  # FastAPI gateway + capability services
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── mcp_server.py     # IBM Bob MCP tools/resources/prompts
│   │   │   ├── models.py
│   │   │   ├── reference.py      # REAL POLB terminals + constants
│   │   │   ├── seed.py           # reference seed + SimPy layer
│   │   │   ├── routers/
│   │   │   └── services/
│   │   ├── pyproject.toml
│   │   └── .env.example
│   ├── frontend/                 # React + Vite dashboard
│   └── README.md
├── submission.yaml               # Hackathon submission manifest
├── .bob/                         # Bob project MCP config, rules and skill
├── docs/                         # problem · solution · architecture · setup
├── demo/                         # screenshots + demo video link/script
├── presentation/                 # deck (see presentation/README.md)
├── IMPLEMENTATION_STATUS.md
└── CONTRIBUTING.md
```

---

## ⚡ How to Run

```bash
git clone https://github.com/Aryan-B-Parikh/404-Team-Not-Found.git
cd 404-Team-Not-Found

# One command (seeds if empty, starts backend :8000 + frontend :5173)
./scripts/dev.sh
# or manually:

# PostgreSQL database
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

### 🌍 Production deployment

The stack deploys as three units — **frontend on Vercel**, **FastAPI backend on Voroa**, and
**PostgreSQL on Supabase** (already provisioned and seeded): the Vercel project proxies `/api/*`
and `/health` to the Voroa web service via `src/frontend/vercel.json` rewrites, so the browser
talks to a single origin with no CORS setup. The backend self-bootstraps (schema + seed +
weather/tide pipelines) against the Supabase pooler on first boot.
Full step-by-step guide: [`docs/deployment.md`](docs/deployment.md).

**Verify:** open `http://localhost:5173`, inspect Overview / Forecast / Berth & Cranes / 72-Hr Plan, then open **Bob AI** and ask: *"What's the biggest operational risk over the next 72 hours?"*

---

## 🖥️ Demo

| Artifact | Location |
|---|---|
| 📹 Demo Video | [`demo/demo-video-link.txt`](demo/demo-video-link.txt) |
| 🌐 Live Demo | [`demo/live-demo-url.txt`](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [`demo/screenshots/`](demo/screenshots/) |
| 📊 Presentation | [`presentation/portpulse_ai.pdf`](presentation/portpulse_ai.pdf) |
| 📦 Submission manifest | [`submission.yaml`](submission.yaml) |

---

## 🧪 Data honesty — what is real, what is demo

- **REAL:** Port of Long Beach terminal/berth/crane/yard/gate reference capacity used as hard operational constraints.
- **DEMO_AIS:** the default offline vessel/congestion history is synthetic and reproducible. It is explicitly labelled `DEMO_AIS` and is **not measured AIS**.
- **AIS:** a real NOAA AccessAIS CSV can be imported through `POST /api/ais/import`; imported observations are labelled `AIS`.
- **Open-Meteo:** weather features are fetched through the weather pipeline when available.

The hybrid approach is intentional because public feeds do not provide a complete live terminal TOS dataset.

---

## ⚠️ Known Limitations

- Default operational history is synthetic `DEMO_AIS`; no live TOS/AIS stream is connected.
- The optimiser covers four POLB container terminals / 13 working berths rather than the complete port-wide estate.
- Tidal windows are represented through depth constraints rather than a dynamically solved harmonic tide model.
- The shipped scenario is deliberately oversubscribed; cargo volume is not part of the optimisation objective.
- Caching is in-memory; vessel ETAs remain fixed unless schedule data is uploaded.
- Cold forecast/optimisation/full-plan execution is slower than a production dispatch system; warm cached requests are substantially faster.

---

## 🏅 What We're Most Proud Of

The strongest part of PortPulse AI is the **agentic decision loop**. IBM Bob does not merely summarize a static dashboard: it selects the relevant MCP tools, executes the actual domain engines, receives their structured outputs, and synthesizes the evidence into an operational recommendation. The deterministic fallback uses the same engine results and does not pretend to be another AI provider.

---

## 📚 Documentation index

- [`docs/problem-statement.md`](docs/problem-statement.md)
- [`docs/solution-overview.md`](docs/solution-overview.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/setup-guide.md`](docs/setup-guide.md)
- [`docs/deployment.md`](docs/deployment.md) — Vercel (frontend) + Voroa (backend + PostgreSQL)
- [`src/README.md`](src/README.md)
- [`docs/bob-mcp.md`](docs/bob-mcp.md)
- [`docs/api-contract.md`](docs/api-contract.md)
- [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
