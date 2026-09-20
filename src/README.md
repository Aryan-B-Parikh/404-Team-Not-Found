# src/ — PortPulse AI monorepo

The source tree implements the focused decision loop: **observe → predict → explain risk → optimise → route → plan → Bob**.

```text
src/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI gateway
│   │   ├── config.py            # environment/settings
│   │   ├── db.py                # PostgreSQL / SQLAlchemy
│   │   ├── models.py            # operational data model
│   │   ├── reference.py         # real POLB terminal capacity
│   │   ├── seed.py              # reference + SimPy demo data
│   │   ├── mcp_server.py        # IBM Bob MCP tools/resources/prompts
│   │   ├── pipelines/            # AIS, weather, BTS and schedule ingestion
│   │   ├── routers/              # FastAPI capability routes
│   │   └── services/
│   │       ├── simulation.py    # SimPy operations layer
│   │       ├── forecasting.py   # LightGBM + uncertainty bands
│   │       ├── anomaly.py       # Isolation Forest disruption detection
│   │       ├── hotspot.py       # risk + binding-resource attribution
│   │       ├── optimiser.py     # OR-Tools CP-SAT BAP/QCAP + FIFO
│   │       ├── routing.py       # routing decision engine
│   │       ├── plan.py          # 12 × 6h plan + provenance
│   │       ├── bob.py           # shared engine-grounded assistant
│   │       ├── bob_agent.py     # real IBM Bob CLI integration
│   │       ├── llm.py           # Bob/deterministic provider resolution
│   │       └── pipeline.py      # orchestration + persistence + caching
│   ├── pyproject.toml
│   ├── bob-mcp.config.json
│   └── .env.example
│
├── frontend/                    # React + Vite operational cockpit
│   ├── src/
│   │   ├── tabs/                # overview, forecast, berth, routing, plan, Bob
│   │   ├── pages/               # congestion heatmap, quality, scenarios
│   │   └── features/             # map/heatmap + scenario components
│   └── index.html
└── README.md
```

## Technology map

| Layer | Technology |
|---|---|
| API | FastAPI / Python 3.11 |
| Simulation | SimPy |
| Forecast | LightGBM quantile regression |
| Anomaly | scikit-learn Isolation Forest |
| Optimisation | Google OR-Tools CP-SAT |
| Database | PostgreSQL / SQLAlchemy |
| Dashboard | React / Vite / Tailwind / Recharts / MapLibre |
| Agent | IBM Bob + Model Context Protocol |

IBM Bob is the only AI-agent provider. If Bob is unavailable, the application uses a deterministic briefing from the same engine outputs. There is no Claude or other external-LLM fallback.

Full setup: [`../docs/setup-guide.md`](../docs/setup-guide.md).
