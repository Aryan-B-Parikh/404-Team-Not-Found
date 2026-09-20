# PortPulse AI — Python backend

FastAPI gateway + capability services implementing the core L1 architecture:

| Capability | Technology | Module |
|---|---|---|
| Gateway / API | FastAPI | `app/main.py`, `app/routers/*` |
| Simulation | SimPy discrete-event | `app/services/simulation.py` |
| Congestion forecasting | LightGBM + quantile bands | `app/services/forecasting.py` |
| Anomaly / disruption | scikit-learn Isolation Forest | `app/services/anomaly.py` |
| Hotspot / bottleneck | deterministic risk scorer | `app/services/hotspot.py` |
| Berth/crane optimisation | Google OR-Tools CP-SAT | `app/services/optimiser.py` |
| Routing | deterministic decision engine | `app/services/routing.py` |
| 72h plan | plan assembler | `app/services/plan.py` |
| Agent | IBM Bob via MCP | `app/services/bob_agent.py`, `app/mcp_server.py` |
| Persistence | PostgreSQL + SQLAlchemy | `app/models.py`, `app/db.py` |

## Run

```bash
uv sync --python 3.11
createdb -U postgres portflow
cp .env.example .env
# Set DATABASE_URL and BOB_API_KEY locally.
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000
```

## Architecture

```text
Real POLB capacity + labelled DEMO_AIS + weather
                    ↓
          SimPy / data context
                    ↓
      LightGBM + Isolation Forest
                    ↓
       Risk / binding-resource layer
                    ↓
            OR-Tools CP-SAT
                    ↓
      Routing + 72-hour operations plan
                    ↓
             IBM Bob via MCP
                    ↓
       Supervisor-facing explanation
```

IBM Bob is the only AI-agent provider. If Bob is unavailable, the application uses a deterministic template over the same engine outputs; there is no Claude or other external-LLM fallback.
