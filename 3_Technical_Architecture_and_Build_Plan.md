# PORTPULSE AI
# TECHNICAL ARCHITECTURE, BUILD PLAN & DEMO SCRIPT

*L1: Container Congestion Predictor & Port Operations Optimiser — Execution Plan*

---

## 1. Recommended Tech Stack

| Layer | Choice & rationale |
|---|---|
| Frontend / Dashboard | React + Vite, Recharts/D3 for heatmap & Gantt, Tailwind for styling |
| Backend API | FastAPI (Python) — one service per capability, behind a single gateway |
| Forecasting | Python: gradient-boosted trees (LightGBM/XGBoost) for a 24–72h horizon, or a simple LSTM if time allows; scikit-learn for anomaly detection (Isolation Forest) |
| Optimisation (Berth/Crane) | Google OR-Tools (CP-SAT) for the Berth Allocation Problem / Quay Crane Assignment Problem as a constraint-satisfaction / MIP model |
| Simulation (synthetic ops data) | SimPy discrete-event simulation for berth/crane/yard/gate state generation |
| Database | PostgreSQL for relational entities, TimescaleDB extension (or plain partitioned tables) for AIS/time-series |
| LLM layer | LLM via the agent layer — used only for the 72-hour plan narrative and explanation text, never for numeric scheduling (shipped as IBM Bob via MCP; deterministic fallback) |
| Data pipeline | Python scripts / lightweight Airflow-style DAG for batch loads (AIS, BTS, weather) |

---

## 2. System Architecture (Description)

**Data layer:** MarineCadastre AIS extract + BTS PPFSP benchmarks + Open-Meteo weather feed load into PostgreSQL/Timescale on a schedule; SimPy generates synthetic live berth/crane/yard/gate state and streams it into the same database, timestamped as if it were real TOS telemetry.

**Service layer:** (1) Forecasting Service reads historical + live state and produces congestion forecasts with uncertainty bands; (2) Hotspot Service ranks bottlenecks from those forecasts; (3) Optimisation Service (OR-Tools CP-SAT) consumes the vessel schedule + capacity constraints and produces a berth/crane assignment plan; (4) Plan Service assembles forecasts + assignments into a 72-hour operations plan and calls the LLM only to phrase it.

**Presentation layer:** FastAPI gateway exposes read endpoints to the React dashboard, which renders the congestion heatmap, the 72-hour Gantt of berth/crane assignments, KPI cards, and the scenario simulator controls.

---

## 3. Data Pipeline Plan

- Batch-load a 3–6 month AIS GeoParquet window for one chosen real port into PostgreSQL.
- Batch-load matching BTS PPFSP weekly berthing statistics for benchmarking.
- Compute inter-arrival and dwell-time distributions by vessel size class from the AIS load.
- Configure and run the SimPy simulation seeded with those distributions to produce the synthetic 6-berth/12-crane/4-yard terminal's operational time series.
- Pull Open-Meteo historical + forecast weather for the same port coordinates.
- Expose all of the above through a single normalised schema (see Module D/E of the Requirements document) so the forecasting and optimisation services don't need source-specific logic.

---

## 4. Forecasting & Optimisation Approach — Detail

### 4.1 Congestion Forecasting
- Target variables: queue length, berth-wait time, yard utilisation, each at 24/48/72h horizons.
- Features: historical arrivals, day-of-week/seasonality, current utilisation, weather, count of vessels due to arrive in the next N hours (bunching signal).
- Model: start with LightGBM quantile regression (gives you the uncertainty band almost for free); upgrade to an LSTM/temporal model only if time and data volume support it.

### 4.2 Berth Allocation & Crane Assignment
- Formulate as a Berth Allocation Problem (BAP): decision variables = berth assignment and start time per vessel; hard constraints = berth length/depth ≥ vessel LOA/draft, no time-overlap on the same berth, tidal windows; objective = minimise weighted total wait time + makespan.
- Add a Quay Crane Assignment Problem (QCAP) layer on top: assign 1–3 cranes per berthed vessel from the available pool, respecting crane availability and a workload-balance term.
- Solve with OR-Tools CP-SAT for the demo-scale instance (6 berths, ~15–20 vessels over 5 days solves in seconds); re-solve incrementally when a single vessel ETA changes rather than from scratch.

---

## 5. Build Plan (48–72 Hour Hackathon Timeline)

| Slot | Deliverable |
|---|---|
| Day 0 (Prep) | Pick reference port; pull AIS + BTS + Open-Meteo data; define synthetic terminal parameters; agree on schema. |
| Day 1 AM | Data pipeline live: AIS/BTS loaded, SimPy simulation producing synthetic live state, schema populated. |
| Day 1 PM | Forecasting model v1 trained and serving; hotspot ranking logic implemented on top of it. |
| Day 2 AM | OR-Tools berth/crane optimiser working on the synthetic vessel schedule; validated against hard constraints. |
| Day 2 PM | Dashboard: KPI cards, congestion heatmap, 72-hour Gantt wired to live services; scenario simulator (one scenario) added. |
| Day 3 AM | LLM plan-narrative layer; explainability surfacing (Module M); edge-case handling (Section 22 of Requirements doc). |
| Day 3 PM | Demo scenario rehearsal, bug fixes, pitch deck, and this document set finalised. |

---

## 6. Module-to-Task Mapping (for parallel work)

- **Data & simulation owner:** Modules A–E (reference data, ingestion, normalisation, SimPy synthetic ops layer).
- **ML owner:** Modules F & H (forecasting, anomaly detection).
- **Optimisation owner:** Modules G & J (hotspot ranking + BAP/QCAP solver).
- **Product/Frontend owner:** Modules K (plan rendering), L (scenario UI), N (dashboard/heatmap/Gantt).
- **Integration/Explainability owner:** Module M, LLM plan-narrative wiring, demo script and edge-case rehearsal.

---

## 7. Demo Script / Pitch Narrative

- Open on the dashboard showing the synthetic terminal in a normal state — queue short, utilisation moderate.
- Fast-forward the simulation clock: three post-panamax vessels are now forecast to bunch in the next 24–36 hours.
- Congestion heatmap lights up on Terminal 2; hotspot panel attributes it to berth availability + one crane under maintenance, with confidence shown.
- Click into the recommendation: alternate berth window suggested for two vessels, one crane reassigned from Terminal 1.
- Show the 72-hour Gantt updating to the optimised plan, and the plain-language plan text generated for the shift supervisor.
- Show baseline-vs-optimised comparison: total wait time reduced, no hard constraint violated.
- Close by naming the real data sources used (AIS, BTS) versus the clearly-labelled synthetic operational layer, reinforcing the explainability/trust story.

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| OR-Tools solve time grows with instance size | Keep demo instance small (6 berths, ~15–20 vessels); pre-warm the solver. |
| Forecasting model has too little historical data for the chosen port window | Widen the historical window; fall back to a simpler baseline (moving average + seasonal factor) with explicit low-confidence labelling. |
| Live demo data feed (weather API) fails during presentation | Cache a local snapshot of the weather pull as a fallback. |
| Judges question the synthetic operational data | Lead with the transparency story: real AIS/BTS for demand-side truth, clearly labelled simulation for the supply-side data no public dataset covers. |
| Scope creep across 14 modules in a short hackathon | Hold firm to the MVP scope in Section 24 of the Requirements document; everything else is explicitly "Phase 2". |

---

## 9. Acceptance Checklist

- [ ] Data pipeline loads real AIS + BTS + weather data and generates synthetic operational state without manual steps.
- [ ] Forecasting service returns a point estimate and uncertainty band for queue length, wait time, and utilisation.
- [ ] Optimisation service never returns a plan violating a hard constraint.
- [ ] Dashboard renders the congestion heatmap and 72-hour Gantt from live service output, not hard-coded demo data.
- [ ] At least one scenario (equipment outage or bunching) can be simulated and compared to baseline.
- [ ] 72-hour plan text is generated from validated numbers, with the LLM role limited to phrasing.
- [ ] Demo script has been rehearsed end-to-end at least once with the fallback weather snapshot in place.
