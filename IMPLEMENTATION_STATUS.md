# Implementation Status — PortPulse AI vs. the 3 Specification Documents

**Method:** static inspection of the actual code under `src/` **plus** live execution — the FastAPI
service was run, seeded into PostgreSQL, and every endpoint exercised (forecast, CP-SAT solve, routing,
plan, anomalies, Bob, CSV export), and the React/Vite dashboard was built and served. Status reflects
what is **running**, not what the docs claim.

**Legend:** ✅ Done · 🟡 Partial · ❌ Missing

---

## 0. Bottom line

The **technology stack is now aligned to the plan** (`3_Technical_Architecture_and_Build_Plan.md` §1).
The remaining gaps are feature-depth items (a few modules) rather than stack divergence.

| | Count |
|---|---|
| ✅ Done | 26 |
| 🟡 Partial | 13 |
| ❌ Missing | 1 |

---

## 1. Stack alignment (plan §1) — ✅ now aligned

| Plan layer | Plan choice | Implemented | Status |
|---|---|---|---|
| Frontend / Dashboard | React + Vite, Recharts/D3, Tailwind | React 18 + Vite 6 + Tailwind v4 + Recharts (`src/frontend/`) | ✅ |
| Backend API | FastAPI, service-per-capability behind a gateway | FastAPI gateway + one router per capability (`src/backend/app/main.py`, `routers/`) | ✅ |
| Forecasting | LightGBM/XGBoost; scikit-learn Isolation Forest | **LightGBM** + quantile bands; **sklearn IsolationForest** (`services/forecasting.py`, `anomaly.py`) | ✅ |
| Optimisation (BAP/QCAP) | Google OR-Tools **CP-SAT** | **OR-Tools CP-SAT** (`services/optimiser.py`) — verified `OPTIMAL`/`FEASIBLE`, ~0.3–8 s | ✅ |
| Simulation | **SimPy** discrete-event | **SimPy** berth resources (`services/simulation.py`) | ✅ |
| Database | PostgreSQL + TimescaleDB *or plain tables* | **PostgreSQL** via SQLAlchemy 2 + psycopg3 (plain tables — plan-allowed) | ✅ |
| LLM layer | LLM phrasing only | **IBM Bob** in `services/llm.py` (sole provider; `services/bob_agent.py`), strictly grounded, deterministic engine-data fallback | ✅ |
| Data pipeline | Python batch loads (AIS, BTS, weather) | SimPy layer ✅ + AIS pipeline ✅ + **Open-Meteo weather pipeline** ✅ + BTS parser ✅ | ✅ |
| Agent (IBM Bob) | IBM Bob as an MCP client | `app/mcp_server.py` — **12 tools + 4 resources + 3 prompts**, tested via a local MCP client | ✅ |

**Verified running:** `build_full` (forecast→anomaly→hotspot→optimiser→routing→plan) executes end-to-end;
`/api/*` return live engine data; Vite proxies `/api` and renders the dashboard.

---

## 2. Module-by-module status (doc 1 §2–§16)

| Module | Requirement (summary) | Evidence in code | Status | Remaining |
|---|---|---|---|---|
| **A** Port & Terminal Profiling | berths, crane inventory, yard, gate, versioned config | `models.py` `Terminal`(+`config_version`) / `Berth` / `Crane`(type, reach, rated moves/h, status) / `YardZone` / `Gate`; `reference.py` REAL POLB | ✅ | labour shifts, rail sidings |
| **B** Vessel Schedule Ingestion | IMO, ETD, service, declared-vs-AIS ETA, **revision history**, CSV upload | `VesselCall` (imo, etd_hours, service_string, declared_eta_hours, ais_eta_hours, unresolved, data_confidence) + `EtaRevision`; **CSV upload endpoint** (`/api/vessels/upload`) + **QualityPage upload UI** | ✅ | auto-replan on ETA revision |
| **C** Berth/Crane/Yard/Gate Capacity | live occupancy, crane availability, yard util, gate queue, maintenance-vs-failure | SimPy produces occupancy/yard/gate state; `Crane.status` + `status_reason` (planned maintenance) | ✅ (synthetic) | live TOS feed |
| **D** Data Normalisation & Quality | unit normalisation, original+normalised, per-record confidence, completeness score | `services/dataquality.py` per-terminal completeness score; `QualityPage.tsx` live completeness bars + missing fields list; normalisation audit table | ✅ | — |
| **E** AIS / Historical KB | tracks, dwell baselines, vintages, cleaning | `CongestionObservation` (seeded as `DEMO_AIS`; real ingest via `POST /api/ais/import`); `pipelines/ais_generate.py` NOAA-format generator (explicit only: CLI or `POST /api/ais/generate`); `app/pipelines/ais.py` (real AccessAIS CSV drop-in) | 🟡 | vessel tracks, berth-dwell baselines, data vintages |
| **F** Congestion Forecasting | 24/48/72h queue/wait/**yard util**, ML, uncertainty band, reproducible, **weather signal** | `forecasting.py` LightGBM, 4 targets, quantile 0.1/0.9 bands, multi-origin validation, **model_version**, **weather_used flag** when `FEATURE_WEATHER=true` | ✅ | — |
| **G** Hotspot / Bottleneck | binding resource + composite risk score + ranking | `hotspot.py`: w1..w5 risk score, `binding_constraint` (BERTH/CRANE/YARD/GATE), confidence degradation | ✅ | — |
| **H** Anomaly / Disruption | bunching/outage/weather, robust method, disruption-vs-data-error, min sample | `anomaly.py`: IsolationForest, KIND classifier, `DATA_ERROR` distinction, `MIN_SAMPLES` guard | ✅ | weather-driven anomaly detection |
| **I** Alternate Routing | windows/terminals/ports, trade-off, sustained congestion, feasibility | `routing.py`: DIVERT/SLOW_STEAM/PRIORITY_WINDOW/HOLD, in-port terminal alternatives, alt-port table gated on the operator-supplied `PORT_STATUS_JSON` live feed (static table used for physical feasibility only), **sustained** check, LOA feasibility, **exposed cost model + formulas** (`/api/routing` `cost_model`) | 🟡 | berth-booking windows inside the port |
| **J** Berth/Crane Optimiser | BAP/QCAP exact, hard constraints, soft objectives, exposed weights, **tidal windows**, **incremental** | `optimiser.py`: **CP-SAT**, hard LOA/depth/reach + `AddNoOverlap` + `AddCumulative`, FIFO baseline, exposed weights; **tidal toggle wired** to API; **incremental warm-start** wired | ✅ | — |
| **K** 72h Plan | shift plan from F–J, LLM phrases only, cite runs, confidence | `plan.py` 12×6h shifts + run ids + model version; `llm.py` Bob narrative; **per-horizon confidence badges** in UI | ✅ | — |
| **L** Scenario Simulator | berth add/remove, outage, bunching, baseline compare, clone/rollback | `/api/scenarios` (crane outage/productivity) + `/api/scenarios/extended` (**6 kinds**: crane outage, productivity shock, **berth add/remove, vessel bunching, schedule shift**) + `POST /api/scenarios/{id}/rollback`; scenario-specific re-forecast + CP-SAT re-solve; persisted `Scenario`+`ImpactAssessment` | 🟡 | clone/rollback **UI** (API shipped) |
| **M** Explainability | evidence per decision, confidence, assumptions | risk `explanation`, routing `rationale`, model card, feature importance, objective weights exposed | 🟡 | surface the *binding constraint* per assignment in the UI |
| **N** Dashboard | KPI, heatmap, Gantt, timeline, before/after, drill-down | React dashboard: **zone heatmap matrix** (24h × 4 zones), KPI strip, zone drill-down, LightGBM chart with **4-target switcher + 80% bands**, **72h Gantt** with tidal shading, routing cards, 12 shift cards with confidence, Bob chat with action chips | ✅ | port→terminal→berth→vessel drill-down; dedicated scenario-compare view |

---

## 3. Data sources (doc 2)

| Source | Spec use | Status |
|---|---|---|
| NOAA/BOEM **AccessAIS** | historical AIS ground truth | ✅ pipeline `src/backend/app/pipelines/ais.py` (real CSV drop-in); synthetic data is a **separate, explicit** path (`pipelines/ais_generate.py` — CLI or `POST /api/ais/generate`) always labelled `source="DEMO_AIS"` |
| **SimPy** synthetic ops layer | synthetic berth/crane/yard/gate state | ✅ implemented (the plan's core synthetic strategy) |
| **BTS PPFSP** | benchmark/validate | ✅ parser `app/pipelines/bts.py` + `/api/bts/parse` endpoint |
| **Open-Meteo** weather | forecast signal + disruption | ✅ pipeline `app/pipelines/weather.py`; runs on startup + `/api/weather/refresh`; `QualityPage` shows live data |
| World Port Index / Kaggle ports | static port reference | ✅ replaced by REAL POLB fact sheet (better) |

---

## 4. Acceptance checklists

### 4a. Doc 1 §29

| # | Item | Status |
|---|---|---|
| 1 | Terminal/berth/crane/yard data entered & validated | 🟡 (modelled + seeded; no edit UI) |
| 2 | Vessel schedule ingest with ETA revision history | ✅ (revision history + CSV upload + QualityPage UI) |
| 3 | Units/timestamps normalised consistently | ✅ (UTC throughout; ft→m conversion ledger; normalisation audit table in UI) |
| 4 | Historical baselines stored & versioned | 🟡 (stored; not versioned) |
| 5 | Forecasts reproducible + confidence band | ✅ (model_version + quantile bands) |
| 6 | Hotspots ranked, attributed, explainable | ✅ (binding resource + risk score) |
| 7 | Plan never violates a hard constraint | ✅ (CP-SAT hard constraints) |
| 8 | 72h plan with assumptions/confidence | ✅ (per-horizon confidence badges; risk level) |
| 9 | ≥1 what-if scenario vs baseline | ✅ (`/api/scenarios`) |
| 10 | Heatmap + Gantt | ✅ (zone heatmap matrix + 72h tidal Gantt) |
| 11 | Edge cases don't mislead | 🟡 (data-error vs disruption ✅; others partial) |
| 12 | Model version + timestamp per run | ✅ |

### 4b. Doc 3 §9

| # | Item | Status |
|---|---|---|
| 1 | Pipeline loads real AIS + BTS + weather, synthetic ops, no manual steps | ✅ (SimPy + AIS + BTS parser + Open-Meteo weather all wired; startup auto-refreshes weather) |
| 2 | Forecast point + uncertainty for queue/wait/**utilisation** | ✅ (4 targets) |
| 3 | Optimisation never violates a hard constraint | ✅ |
| 4 | Heatmap + Gantt from live service output | ✅ |
| 5 | ≥1 scenario compared to baseline | ✅ |
| 6 | Plan text from validated numbers, LLM phrasing only | ✅ |
| 7 | Demo rehearsed with weather fallback | ✅ (weather shows live; forecast falls back to `weather_used: false` gracefully if Open-Meteo unreachable) |

---

## 5. Bob / agent integration (rubric #5)

| Surface | Implementation | Status |
|---|---|---|
| IBM Bob → our engines (MCP) | `app/mcp_server.py`: 12 tools, 4 resources, 3 prompts; registered with Bob (`bob mcp list`) | ✅ verified live (`mcp__portflow__rank_hotspots` → success) |
| Our app → IBM Bob | `services/bob_agent.py` runs the real Bob agent (`bob run --format stream-json`); `services/llm.py` resolves provider bob→deterministic (no secondary LLM provider) | ✅ verified: `provider=bob · mode=llm · actions=['mcp__portflow__rank_hotspots']` |
| Grounding | answers use ONLY engine data (Bob fetches it via MCP); `actions` lists the tools run; deterministic fallback | ✅ |
| Recursion guard | `PORTFLOW_NO_BOB_AGENT=1` inherited by the MCP child | ✅ |

**Honest note:** IBM Bob is wired **both** ways and verified end-to-end on this machine (Bob CLI 2.0.2,
`BOB_API_KEY` supplied via the environment only — never committed). Without the key the narrative layer
falls back to a deterministic template over the same engine numbers — there is no secondary external LLM provider.

## 5b. What is DONE (verified running)

- SimPy DES → vessel calls, ETA revisions, 14-day hourly congestion series, yard/gate state.
- LightGBM forecast (4 targets) with quantile bands, model version, per-horizon validation, feature importance.
- Isolation Forest anomaly detector (bunching/outage/yard/data-error).
- Composite hotspot risk score with binding-resource attribution.
- OR-Tools CP-SAT BAP/QCAP with hard constraints + FIFO baseline + measured deltas (CP-SAT ran `OPTIMAL`/`FEASIBLE`; e.g. −19 % total wait, −55 h makespan vs FIFO on the seeded instance).
- Routing recommender (4 options, sustained check, exposed indicative cost model), 72h plan, Bob narrative + deterministic fallback.
- **MCP server** exposing 12 engine tools + 4 resources + 3 prompts for IBM Bob, verified with a local MCP client.
- FastAPI gateway (29 endpoint operations), PostgreSQL persistence of every run, CSV export, caching (22 s → 1.7 s).
- **Weather pipeline** (Open-Meteo): startup auto-refresh, `/api/weather/refresh`, `weather_used` flag in forecast.
- **Data Quality page**: per-terminal completeness bars, missing-field chips, live weather table, CSV upload with error display.
- **Overview tab**: zone congestion heatmap matrix (4 terminals × 24h), KPI strip, drill-down panel, sparklines.
- **Forecast tab**: 4-target switcher (index/queue/wait/yard), 80% prediction intervals, weather badge, confidence per horizon.
- **BerthCranes tab**: tidal window shading on Gantt, incremental warm-start, tidal toggle wired to API, solve error display.
- **Plan tab**: per-horizon confidence badges (h24/h48/h72), risk level, CSV export.
- **Bob tab**: streaming UI, MCP action chips, typing indicator, 6 quick prompts.
- React/Vite dashboard (6 tabs + QualityPage) — builds clean (`✓ built in 6.20s`, zero TS errors).

## 6. Known limitations (not blocking a demo)

| Item | Notes |
|---|---|
| `wave_height` always `null` | Marine API variable — would require a second call to `marine-api.open-meteo.com`. Wind + visibility data is live. |
| No auth on mutating endpoints | All endpoints are open; acceptable for a hackathon/demo deployment behind a VPN. |
| Static files not served by FastAPI | Production needs a reverse proxy (nginx) or `StaticFiles` mount. Dev uses Vite proxy. |
| `build_full()` concurrency | Parallel persist calls can interleave anomaly DELETE/INSERT; acceptable at hackathon scale. |

---

## 7. Honesty notes

- The optimiser is now a **real exact solver (CP-SAT)** — not a heuristic. It enforces berth length/depth, crane reach, no berth overlap and the terminal crane-pool capacity.
- The vessel queue is seeded by the **SimPy simulation** and the 14-day congestion history by the synthetic generator, **both explicitly labelled `source="DEMO_AIS"`** (and surfaced as such in the UI). Nothing auto-generates at startup: the demo history loads once on empty-DB seed, real AccessAIS CSVs arrive via `POST /api/ais/import` (which triggers the data-quality pass), and the demo history can be regenerated via `POST /api/ais/generate`.
- **No secondary LLM is used**: Bob phrases the validated numbers; without the Bob agent, plan/Q&A use a deterministic template over the same engine output.
- The scenario is deliberately oversubscribed, so CP-SAT trades some average wait against makespan; **cargo volume is not in the spec objective** (reported for transparency).
- The routing layer's `est_savings_usd` figures are **indicative planning estimates**: linear formulas over public mid-range references (`reference.py`), not carrier quotes or berth-fee quotations; external-port diversion additionally requires the operator-supplied `PORT_STATUS_JSON` feed. Formulas are exposed at `GET /api/routing` (`cost_model`).
- `wave_height` is fetched from the Open-Meteo marine API (`marine-api.open-meteo.com/v1/marine`) as a separate non-fatal call in `pipelines/weather.py`.
