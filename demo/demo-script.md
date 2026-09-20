# PortPulse AI — Demo Video Script & Shot List

> Team **404-Team-Not-Found** · Aryan Parikh (lead) · Mahima Kukadiya
> Target runtime **~14–16 min** (full functionality + database detail). The deck lists a 3–5 min clip; this script is deliberately longer because it walks every working function and the whole data layer.

**How to read this document**

- `[mm:ss]` = timecode
- **SCREEN** = what is on screen
- **DO** = mouse/keyboard actions
- **SAY** = word-for-word voiceover (read at a calm pace)
- **KEY DATA** = specific numbers/labels to point at so the narration stays grounded
- **HONESTY** = the exact real-vs-demo wording to use; do not overclaim

---

## 0. Pre-recording checklist

**Terminal A — backend + database**

```bash
# from repo root
createdb -U postgres portflow            # once, if the DB does not exist
cd src/backend
uv sync --python 3.11
cp .env.example .env                     # set DATABASE_URL; set BOB_API_KEY for live Bob
uv run python -m app.seed                # REAL POLB capacity + DEMO_AIS SimPy layer
uv run uvicorn app.main:app --reload --port 8000
```

**Terminal B — frontend**

```bash
cd src/frontend
npm install
npm run dev                              # http://localhost:5173
```

**Before you hit record**

- [ ] Both servers running; `http://localhost:8000/health` returns `{"status":"ok"}`.
- [ ] Open `http://localhost:5173`, click through **Overview → Forecast → Berths & Cranes → 72-Hour Plan** once to warm the caches (`CACHE_TTL = 120s`) so the recorded run is snappy.
- [ ] Browser window 1440×900, zoom 100%, dark theme, bookmarks bar hidden.
- [ ] Decide Bob mode up front:
  - **Live Bob**: `BOB_API_KEY` set and the `bob` CLI on PATH → the Bob tab shows `IBM Bob · MCP · 12 tools live`.
  - **Fallback**: leave it unset → the tab shows `IBM Bob unavailable · engine fallback`. Say so on camera; the deterministic path uses the same engine numbers.
- [ ] Have a terminal window ready for the **database beat** (`psql portflow`).
- [ ] If you will show `pytest`, run it once so it is fast: `uv run pytest tests/ -q`.

---

## 1. `[0:00–0:45]` Title & hook

- **SCREEN:** Title card — `PortPulse AI — Container Congestion Predictor & Port Operations Optimiser`. Then cut to the terminal running `./scripts/dev.sh`.
- **DO:** Let the seeding log scroll (`terminals: 4  berths: 13  cranes: 62`).
- **SAY:**
  > "San Pedro Bay — the twin ports of Long Beach and Los Angeles — moves billions of dollars of trade. When it congests, the whole country feels it. We're team 404-Team-Not-Found, and this is PortPulse AI: a 72-hour port-operations cockpit that predicts congestion *before* queues form and gives a shift supervisor a physically constrained plan. Python, FastAPI, LightGBM, OR-Tools CP-SAT, SimPy, PostgreSQL, React — and IBM Bob as a load-bearing agent over the Model Context Protocol."
- **KEY DATA:** `terminals: 4 · berths: 13 · cranes: 62`; seed `20240817`.
- **HONESTY:** "REAL Port of Long Beach terminal capacity; the default operational history is labelled `DEMO_AIS` — synthetic and reproducible."

---

## 2. `[0:45–1:45]` Problem statement

- **SCREEN:** `docs/problem-statement.md` (or the deck's Problem slide).
- **DO:** Scroll the analysis; highlight "reactive hotspot discovery", "manual berth planning", "late routing decisions".
- **SAY:**
  > "In the 2021 backlog, operators discovered congestion hotspots *reactively* — after the anchorage had already filled. Berth and crane plans were built by hand. Routing decisions came too late to matter. The cost shows up as anchored ships burning fuel, missed berth windows, and refrigerated cargo at risk. The problem isn't a lack of data — it's that visibility arrives after the decision window has closed."
- **KEY DATA:** 2021 backlog; reactive discovery; manual berth planning; late routing.

---

## 3. `[1:45–3:00]` Architecture & tech stack

- **SCREEN:** `docs/architecture.md` / `docs/solution-overview.md` diagram, then the repo tree (`README.md` → Repository Structure).
- **DO:** Trace the diagram left→right with the cursor.
- **SAY:**
  > "Everything shares one model time `t0`, so the engines can never disagree about 'now'. The REAL POLB capacity table plus a SimPy operations layer land in PostgreSQL. A context loader builds one `EngineContext`, and five engines run in dependency order: LightGBM forecasting with quantile bands, Isolation Forest anomaly detection, a hotspot scorer that names the *binding* resource, an OR-Tools CP-SAT berth-and-crane optimiser, and a congestion-aware routing engine. A pipeline assembles it all; FastAPI serves it to the React dashboard and to IBM Bob's MCP server."
- **KEY DATA:** one shared `t0`; five engine services; `services/pipeline.py` ordering; FastAPI gateway; React/Vite; PostgreSQL (psycopg3); IBM Bob via MCP.
- **SCREEN tip:** show the four capability pillars table from `README.md`:
  1. Predict hotspots — `forecasting.py`+`hotspot.py` — `GET /api/forecast`
  2. Recommend routing — `routing.py` — `GET /api/routing`
  3. Optimise berth & cranes — `optimiser.py` — `GET/POST /api/optimise`
  4. 72h operations plan — `plan.py` — `GET/POST /api/plan`

---

## 4. `[3:00–5:30]` DATABASE DEEP DIVE ⭐

> This is the section you specifically asked for. Budget the most time here.

### 4a. `[3:00–3:40]` Live psql — prove the data is really there

- **SCREEN:** terminal at `psql portflow`.
- **DO:** Run these in order; let each result render.

```sql
-- How many operational rows do we actually have?
SELECT COUNT(*) FROM terminal;                 -- 4
SELECT COUNT(*) FROM berth;                    -- 13
SELECT COUNT(*) FROM crane;                    -- 62
SELECT COUNT(*) FROM vessel_call;              -- vessel calls from the SimPy layer
SELECT COUNT(*) FROM congestion_observation;   -- 14 days x 5 zones hourly

-- Provenance: what is real vs demo?
SELECT source, COUNT(*) FROM congestion_observation GROUP BY source;

-- The REAL Port of Long Beach capacity table
SELECT code, name, pier, berth_length_ft, deepsea_berths, gantry_cranes, capacity_teu_m
FROM terminal ORDER BY code;
```

- **SAY:**
  > "Before any chart, here's the ground truth. Four container terminals, thirteen working berths, sixty-two STS cranes. The `terminal` table is REAL Port of Long Beach fact-sheet data — LBCT on Pier E with 4,200 feet, three deepsea berths, eighteen cranes and 3.5 million TEU capacity; ITS on Pier G; PCT on Pier J with the harbour's longest berth at 5,902 feet; and TTI on Pier T. Notice every congestion observation carries a `source` column: `DEMO_AIS` is our synthetic simulation; `AIS` would be real imported NOAA AccessAIS data."
- **KEY DATA:** 4 terminals · 13 berths · 62 cranes · `source ∈ {DEMO_AIS, AIS}`.

### 4b. `[3:40–5:00]` The entity model — `models.py` code tour

- **SCREEN:** `src/backend/app/models.py` (split view or scroll).
- **DO:** Scroll top→bottom; pause at each group.
- **SAY (group by group):**
  > "Our SQLAlchemy 2 models implement the requirement's entity flow exactly.
  >
  > **Terminal side:** `Terminal → Berth / Crane / YardZone / Gate`. Berth stores physical length and design depth — those become the optimiser's hard constraints. Crane stores outreach and rated moves per hour. Yard stores ground slots and reefer plugs. Gate stores lanes and trucks per hour.
  >
  > **Vessel side:** `VesselCall`, with `EtaRevision`. Crucially, a declared carrier ETA and an AIS-derived ETA are stored *separately* — ETAs are forecasts, not facts. Each vessel has LOA, beam, draft, reefer count, and an `unresolved` flag for incomplete records.
  >
  > **Observation:** `CongestionObservation` — hourly, per zone, for fourteen days, with `is_measured`, `confidence`, and a JSONB `raw` field.
  >
  > **Forecast:** `ForecastRun → ForecastPoint` and `HotspotFlag`. Points store the point estimate plus `lo`/`hi` quantile band; hotspots store the composite risk score, the binding constraint, and the weighted components.
  >
  > **Anomaly:** `AnomalyFlag` — method, score, kind, features.
  >
  > **Optimiser:** `OptimiserRun → Assignment`. The run stores solver status, objective, solve time, the FIFO `baseline`, the `deltas`, and the actual objective `weights` so a supervisor can audit them.
  >
  > **Routing:** `RoutingRecommendation` — option, target port, predicted wait, estimated savings, `sustained` flag, and a JSONB `option_detail`.
  >
  > **Plan and scenarios:** `OperationsPlan` keeps the forecast-run and optimiser-run IDs for lineage. `Scenario → ImpactAssessment` tracks what-if lineage.
  >
  > **Chat:** `ChatMessage` persists Bob's answers with its `actions` and `mode`."
- **KEY DATA:** entity flow from requirements §18; ETAs split declared vs AIS; quantile `lo/hi`; `weights` persisted; plan lineage IDs.
- **HONESTY:** Point at the module docstring: "REAL capacity columns; DEMO_AIS synthetic layer unless replaced by the AIS pipeline."

### 4c. `[5:00–5:30]` Phase-0 tables & data discipline

- **SCREEN:** bottom of `models.py` (`WeatherObservation`, `TerminalQuality`, `TidalWindow`, `VesselScheduleUpload`).
- **SAY:**
  > "Four more tables complete the contract. `WeatherObservation` holds Open-Meteo wind, gust, wave and visibility. `TerminalQuality` holds per-terminal completeness scores. `TidalWindow` makes berth depth time-varying — a real safe-navigation constraint. And `VesselScheduleUpload` is an audit row for every CSV schedule import. The discipline throughout: keep the raw payload in JSONB next to the normalised value, and always record provenance."
- **DO:** Optionally run `\dt` in psql to show all tables at once.

---

## 5. `[5:30–6:30]` Data Quality & Ingestion tab

- **SCREEN:** **Analysis → Data Quality**.
- **DO:** Point to each card; click `Refresh` on completeness; click `Refresh Weather`; hover `Regenerate AIS (14d)` (only click if you have time).
- **SAY:**
  > "This is the ingestion surface. **Terminal Data Completeness** audits each terminal and lists missing fields under a rules version. **Weather** pulls Open-Meteo wind, gusts, waves and visibility, and feeds the forecast as optional features. **AIS Congestion History** shows the source label right on the tile — `DEMO_AIS` amber, `AIS` green — plus observation count, zones, and newest timestamp; the regenerate button rebuilds the fourteen-day synthetic series. **Vessel Schedule Upload** accepts a CSV keyed on IMO and voyage number, returning accepted, rejected, and ETA revisions. And the **Normalisation Audit** table shows every field's raw unit, SI unit, and conversion factor."
- **KEY DATA:** source `DEMO_AIS`/`AIS`; Open-Meteo; required upload columns `imo, voyage_number, declared_eta_hours`; normalisation factor table.

---

## 6. `[6:30–7:00]` Overview — live operations cockpit

- **SCREEN:** **Command → Overview**.
- **DO:** Hover KPI cards; click a zone card (e.g. LBCT) to open the drill-down; expand the anomalies table.
- **SAY:**
  > "The cockpit opens on live KPIs: port index, 72-hour peak at its hour, vessels at anchor versus inbound, average and maximum wait, berth and crane utilisation, pending moves, fleet burn per day, and 24-hour arrivals. The heatmap shows twenty-four hours of history across the four terminals. Clicking a zone opens a drill-down with peak index, queue, yard utilisation, and — if it's a hotspot — the risk score and the *binding resource*. Behind all of this is the SimPy simulation: a discrete-event model where each berth is a capacity-one resource, vessels queue in an observable anchorage, work for moves over cranes times rate, and fill the yard and gate. It's deterministic given seed 20240817."
- **KEY DATA:** 9 KPI cards; 24h heatmap; SimPy seed `20240817`; binding resource = BERTH/CRANE/YARD/GATE.

---

## 7. `[7:00–8:00]` Forecast tab — LightGBM with uncertainty

- **SCREEN:** **Command → Forecast**.
- **DO:** Switch zone dropdown Port → LBCT; toggle targets **Congestion index / Queue / Avg wait / Yard utilisation**; hover the chart to show the shaded band; expand **Model details & accuracy**.
- **SAY:**
  > "The forecast engine is LightGBM. For each zone and each target — congestion index, queue length, average wait, and yard utilisation — we train a point regressor plus two quantile regressors at the tenth and ninetieth percentiles, which gives the eighty-percent prediction band you see shaded. The horizon is a recursive one-step rollout to 24, 48 and 72 hours. Features include lag and rolling congestion, hour-of-day, day-of-week, ETA arrival pressure — that's vessel bunching — berth load factor, yard utilisation, and optional weather. Validation is a 48-hour holdout with MAE, R-squared, and skill against a persistence baseline, plus multi-origin rollouts per horizon. Every run carries a model version so results are reproducible."
- **KEY DATA:** point + 0.1/0.9 quantiles; 24/48/72h; 80% band; MAE/R²/skill vs persistence; model version.
- **SCREEN tip:** the `Model card` shows Algorithm, Model version, Training rows, Holdout, MAE ≤24h/≤72h, R²/skill, band coverage.

---

## 8. `[8:00–8:45]` Anomalies & hotspots

- **SCREEN:** Overview → expand **Isolation Forest anomalies**; then **Command → Congestion** for hotspot ranking.
- **DO:** Expand the anomaly table; on Congestion, click a terminal card to open the drawer.
- **SAY:**
  > "Two detection layers. An **Isolation Forest**, per zone, over a seven-feature window — index, queue, wait, yard, delta-queue, delta-index, rolling sigma — classifies anomalies as bunching, outage, yard saturation, or variance, and separates a likely *data error* from a genuine disruption. It refuses to assert below ninety-six hours of samples. Then the **hotspot engine** builds a composite risk score: queue, utilisation, variance, forecast uncertainty, and disruption signal, weighted 0.34, 0.24, 0.16, 0.16, 0.10. Because utilisation is the maximum pressure across berth, crane, yard and gate, the module names the *binding* resource — not just the busiest terminal."
- **KEY DATA:** Isolation Forest; MIN_SAMPLES 96h; kinds BUNCHING/OUTAGE/YARD_SATURATION/VARIANCE/DATA_ERROR; weights 0.34/0.24/0.16/0.16/0.10.

---

## 9. `[8:45–10:15]` Berths & Cranes — OR-Tools CP-SAT ⭐

- **SCREEN:** **Operations → Berths & Cranes**.
- **DO:** Drag **Crane availability** to ~75% and **STS productivity** to ~24 moves/h; tick **Tidal windows**; click **Run scenario**; wait for `OPTIMAL/FEASIBLE`; show the Gantt; switch to **CP-SAT vs FIFO**.
- **SAY:**
  > "This is a real optimisation solve, not a heuristic. We formulate Berth Allocation plus Quay-Crane Assignment as a CP-SAT model. Decision variables are berth assignment, crane count — from two up to the berth maximum, capped at eight — and start time per vessel, modelled as optional fixed-size intervals per vessel, berth and crane count. The hard constraints are physical: length overall must fit the berth length, draft must fit the design depth, beam must fit the crane outreach. Berths can't overlap — `AddNoOverlap` — and per terminal the simultaneous cranes can't exceed the available pool — `AddCumulative`. A vessel must *start* inside the 72-hour horizon or it's deferred. The objective weights priority-weighted wait, makespan, crane use, and throughput, and we expose those weights on screen. We solve a FIFO first-fit baseline alongside it, so you can see the measured delta. On the seeded instance CP-SAT cuts total wait by about nineteen percent and makespan by roughly fifty-five hours at the same service count. The shaded bands on the Gantt are low-water tidal windows — time-varying depth constraints."
- **KEY DATA:** OR-Tools CP-SAT; crane count 2…min(berth max, 8); LOA/draft/beam constraints; `AddNoOverlap` + `AddCumulative`; ~−19% wait; ~−55h makespan; solve ~0.3–8s cached.
- **HONESTY:** "The shipped scenario is deliberately oversubscribed; this covers four POLB container terminals and thirteen working berths, not the entire port estate."

---

## 10. `[10:15–11:00]` Routing tab — congestion-aware decisions

- **SCREEN:** **Operations → Routing**.
- **DO:** Click filter pills `DIVERT`, `SLOW STEAM`, `PRIORITY WINDOW`, `HOLD`; open one **View Recommendation Details** drawer.
- **SAY:**
  > "Every vessel gets one of four actions: divert, slow-steam, priority window, or hold. The recommendation uses the forecast wait at the vessel's destination zone, and we only recommend a divert when congestion is *sustained* — at least three consecutive forecast hours above the threshold — so a single noisy point can't trigger a diversion. The economics are explicit: thirty-two thousand dollars per day ship operating cost, one hundred eighty dollars per reefer unit of spoilage risk, and an alternative-port table with availability buffers for Oakland, Seattle-Tacoma, Prince Rupert, Ensenada and more. The top strip totals the fleet's potential savings."
- **KEY DATA:** DIVERT/SLOW_STEAM/PRIORITY_WINDOW/HOLD; ≥3 consecutive hours; $32,000/day; $180/reefer; alt-port distances/depths.

---

## 11. `[11:00–11:45]` 72-Hour Operations Plan

- **SCREEN:** **Operations → 72-Hour Plan**.
- **DO:** Point at the traceability line; show KPI strip; expand **Remaining shifts**; hover **Export CSV**.
- **SAY:**
  > "The plan turns all of that into twelve six-hour shifts. Each shift lists arrivals, berthings with berth and crane counts, congestion alerts at watch, warn and critical levels — thresholds 45, 60 and 75 — routing decide-by deadlines, and a supervisor checklist. The header is the part auditors care about: it cites the plan ID, the forecast run ID, and the optimiser run ID, so every number traces back to the exact engine run that produced it. Bob rewrites it for a supervisor strictly from those numbers, with a deterministic fallback."
- **KEY DATA:** 12 × 6h shifts; alerts WATCH 45 / WARN 60 / CRIT 75; provenance run IDs; CSV export.

---

## 12. `[11:45–12:30]` Scenario Center — stress testing

- **SCREEN:** **Analysis → Scenarios**.
- **DO:** Pick a preset; drag the crane-availability and move-rate sliders; click **Execute Simulation**; show the comparison KPIs and grouped bar chart.
- **SAY:**
  > "The Scenario Center stress-tests the plan. Pick a preset or tune the sliders — crane availability from fifty to one hundred percent, throughput from twenty to thirty-five moves per crane-hour — and the CP-SAT engine re-solves the same instance. We compare baseline versus scenario on vessels serviced, container moves, average wait, and a fleet economic impact using the thirty-two-thousand-dollar-per-day model. Notice the honesty note: the engine returns solver-level totals, so we draw exactly those bars and no per-shift trajectory that wasn't computed."
- **KEY DATA:** preset + custom sliders; live `POST /api/scenarios`; impact KPIs; "no fabricated trajectory".

---

## 13. `[12:30–14:00]` IBM Bob — the load-bearing agent ⭐

- **SCREEN:** **AI → Bob AI**, then `.bob/mcp.json` and `src/backend/app/mcp_server.py`.
- **DO:** Ask *"What's the biggest operational risk over the next 72 hours?"* — then *"Compare CP-SAT against FIFO and explain the operational gain."* — then *"Simulate a 25% crane-capacity outage. What changes and what should we do?"* Point at the tool chips under each answer and the mode chip.
- **SAY:**
  > "Bob is not a decorative chat layer — it's the orchestrator, and it's load-bearing in both directions. Our MCP server exposes twelve operational tools, four resources and three prompts. When you ask Bob a question, Bob acts as the MCP client: it selects the right tools — forecast congestion, rank hotspots, optimise berth and cranes, simulate a scenario — actually executes our engines, receives their structured output, and writes the supervisor-facing answer. The little chips under each reply are the real tool calls Bob made, and the mode chip shows whether this is live IBM Bob or the engine fallback. There's an important safety gate: an answer with zero tool calls is rejected server-side, because a reply that never touched the engines can't be trusted. And if Bob is unavailable, we don't call some second LLM — we serve a deterministic briefing over the exact same engine numbers. The provenance story stays clean."
- **KEY DATA:** 12 tools / 4 resources / 3 prompts; `optimise_berth_cranes`, `simulate_scenario`, `forecast_congestion`; tool-evidence gate; provider = `bob` or `deterministic`.
- **SCREEN tip:** show the tool registry in `mcp_server.py` and the `agent_grounding_verdict` function in `services/bob.py`.

---

## 14. `[14:00–14:45]` Impact & close

- **SCREEN:** Overview or the Impact slide; then the live demo URL.
- **SAY:**
  > "So what changed? Warning arrives before the queue forms — 72 hours ahead with uncertainty bands. Schedules are physically feasible, because the optimiser respects berth length, draft, outreach and crane pools. Routing is economically informed instead of reactive. Shift handover is one generated plan. And every claim is auditable — real POLB capacity, clearly labelled synthetic history, and engine run IDs on the plan. PortPulse AI. Thank you."
- **KEY DATA:** live demo URL (`demo/live-demo-url.txt`); repo link; demo video (`demo/demo-video-link.txt`).

---

## Appendix A — Optional insert shots

- **API surface:** open `http://localhost:8000/docs` (Swagger) and expand `/api/forecast`, `/api/optimise`, `/api/plan`.
- **Contract proof:** `src/backend/openapi.json` → `src/frontend/src/lib/api-types.gen.ts` (typed frontend against a frozen contract).
- **Tests:** in `src/backend`, run `uv run pytest tests/ -q` and show the contract/engine tests passing.
- **MCP server config:** `demo` of `.bob/mcp.json` pointing Bob at `app.mcp_server`.

## Appendix B — Claims-honesty crib sheet

Say these exact framings if asked:

- **REAL:** Port of Long Beach terminal/berth/crane/yard/gate reference capacity (fact sheets) used as hard constraints.
- **DEMO_AIS:** default vessel and congestion history is synthetic, reproducible, and labelled `DEMO_AIS` — *not* measured AIS.
- **AIS:** a real NOAA AccessAIS CSV can be imported via `POST /api/ais/import` and is then labelled `AIS`.
- **Weather:** Open-Meteo, fetched when reachable.
- **LLM:** IBM Bob only. The fallback is deterministic over engine numbers — there is no secondary external LLM provider.
- **Scope:** four POLB container terminals / thirteen working berths; tides are depth constraints, not a solved harmonic model.

## Appendix C — Timing summary

| Section | Time | Cumulative |
|---|---|---|
| Title & hook | 0:45 | 0:45 |
| Problem | 1:00 | 1:45 |
| Architecture | 1:15 | 3:00 |
| Database deep dive | 2:30 | 5:30 |
| Data Quality | 1:00 | 6:30 |
| Overview | 0:30 | 7:00 |
| Forecast | 1:00 | 8:00 |
| Anomalies & hotspots | 0:45 | 8:45 |
| Berths & Cranes | 1:30 | 10:15 |
| Routing | 0:45 | 11:00 |
| 72-Hour Plan | 0:45 | 11:45 |
| Scenarios | 0:45 | 12:30 |
| IBM Bob | 1:30 | 14:00 |
| Impact & close | 0:45 | 14:45 |
