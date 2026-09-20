# CONTAINER CONGESTION PREDICTOR
# & PORT OPERATIONS OPTIMISER

*Hackathon Problem Analysis, Module-wise Requirements, Winning Solution & Edge Cases*

*Prepared as a student implementation and presentation handoff document*

---

## 1. Problem Statement Analysis

**Problem:** Port operators still allocate berths, cranes, and yard space across hundreds of vessels manually in spreadsheets. Congestion hotspots are identified reactively — after vessels are already queuing — and alternate-routing decisions come too late to matter. The 2021 LA/Long Beach backlog (100+ ships waiting offshore for weeks, $10B+ in global supply-chain cost) is the canonical example of what happens when this is done reactively instead of predictively.

**Primary users:** Port/terminal operations managers, shift supervisors, berth planning teams, vessel agents, carriers deciding on routing, and regional port authorities.

**Winning interpretation:** The product must forecast congestion before it happens using vessel schedules and berth/yard/crane capacity data, recommend alternate routing or timing strategies, optimise berth and crane assignments under real operational constraints, and hand a shift supervisor a concrete 72-hour operations plan — not just a dashboard of current status.

### 1.1 What the solution should NOT become

- A live map that only shows where ships currently are (that is monitoring, not prediction or optimisation).
- An LLM-only chatbot that invents ETAs, berth availability, or crane throughput numbers.
- A congestion score with no underlying cause (berth-limited vs. yard-limited vs. crane-limited vs. gate-limited) and no recommended action.
- A berth/crane schedule that ignores hard constraints (vessel draft, berth length, crane reach, tidal windows, labor shift limits) and is therefore operationally unusable.
- A system that cannot explain why it predicted a hotspot or why it ranked one routing/berthing option over another.

### 1.2 Recommended Product Concept

**PortPulse AI:** Container Congestion Forecaster & Berth/Crane Operations Copilot

**Design principle:** Use deterministic queuing/operations-research models for berth allocation, crane assignment, and yard-space optimisation (these are constraint-satisfaction and scheduling problems with a long, well-understood OR literature). Use ML/time-series forecasting for congestion prediction and anomaly detection. Use an LLM only to turn the optimiser's output into a readable 72-hour plan and to explain rankings — never to invent schedules, ETAs, or capacity numbers.

---

## 2. Module Overview

| Module | Name |
|---|---|
| A | Port & Terminal Profiling |
| B | Vessel Schedule & Voyage Data Ingestion |
| C | Berth, Crane, Yard & Gate Capacity Data |
| D | Data Normalisation & Quality Engine |
| E | AIS / Historical Congestion Knowledge Base |
| F | Congestion Forecasting Engine |
| G | Hotspot / Bottleneck Detector |
| H | Anomaly & Disruption Detector |
| I | Alternate Routing & Diversion Recommender |
| J | Berth Allocation & Crane Assignment Optimiser |
| K | 72-Hour Port Operations Plan Generator |
| L | Scenario Simulator / What-If |
| M | Recommendation Explainability |
| N | Dashboard & Visualisation |

---

## 3. Module A — Port & Terminal Profiling

### Functional Requirements
- Port/terminal name, location, number of berths, berth lengths and depths, max vessel draft per berth.
- Crane inventory per berth (type, reach, rated moves/hour) and yard capacity (TEU ground slots, reefer plugs).
- Gate operating hours, truck lanes, rail siding capacity if applicable.
- Labor shift patterns and crew availability windows.

### Validation / Technical Requirements
- Every physical constraint (draft, length, crane reach) must be stored and enforced downstream — never assumed.
- Terminal configuration must be versioned since berths/cranes get added, removed or go under maintenance.
- Location must be captured for weather/tide joins.

---

## 4. Module B — Vessel Schedule & Voyage Data Ingestion

### Functional Requirements
- Ingest vessel call schedules: IMO number, vessel name, size (TEU capacity, LOA, draft), ETA, ETD, carrier, service string.
- Support manual entry, CSV/EDI upload, and (optional) live AIS feed ingestion.
- Capture cargo exchange volume (containers to discharge/load) per call where available.
- Track schedule revisions (ETA updates) as a time series, not just the latest value.

### Validation / Technical Requirements
- ETAs are forecasts, not facts — store both the carrier-declared ETA and any AIS-derived ETA separately.
- A vessel may appear multiple times (schedule change) — dedupe on IMO + voyage number, not name alone.
- Missing draft/size data must not silently default to an average; flag as unresolved.

---

## 5. Module C — Berth, Crane, Yard & Gate Capacity Data

### Functional Requirements
- Real-time/near-real-time berth occupancy status (occupied/vacant, vessel assigned, expected release time).
- Crane availability and current assignment per berth.
- Yard utilisation by block/zone (used vs. total TEU ground slots).
- Gate throughput (trucks processed per hour) and current queue length.

### Validation / Technical Requirements
- Distinguish planned maintenance downtime from unplanned equipment failure.
- Berth occupancy must reconcile against the vessel schedule (module B) to catch data drift.
- Yard data may be delayed/batched — timestamp every reading with its true observation time.

---

## 6. Module D — Data Normalisation & Quality Engine

### Functional Requirements
- Normalise units (TEU vs. FFE, metric vs. imperial draft, local time vs. UTC) to internal standards.
- Store original value/unit alongside normalised value/unit.
- Assign a data-quality/confidence score to each ingested record.
- Generate a per-terminal Data Completeness Score used to gate downstream forecasting confidence.

### Validation / Technical Requirements
- Never silently convert an ambiguous unit — flag it for review instead.
- Keep all conversion and normalisation rules versioned and reproducible.
- Separate measured (sensor/AIS-derived) values from estimated/manually entered values.

---

## 7. Module E — AIS / Historical Congestion Knowledge Base

### Functional Requirements
- Store historical vessel tracks, anchorage dwell times, berth dwell times, and turnaround times by vessel class.
- Maintain rolling baselines per terminal (median wait time, median berth-to-berth time) for anomaly comparison.
- Support multiple data vintages (e.g. pre/post equipment upgrade) so historical comparisons stay fair.

### Validation / Technical Requirements
- AIS data has known gaps and spoofing/noise issues near anchorages — apply trajectory-cleaning before using it as ground truth.
- Historical baselines must be recomputed periodically, not hard-coded once.

---

## 8. Module F — Congestion Forecasting Engine (core ML)

### Functional Requirements
- Forecast, for a rolling 24/48/72-hour horizon: expected vessel queue length, expected berth-wait time, and expected yard-utilisation ceiling per terminal/zone.
- Use time-series models (e.g. gradient-boosted trees or LSTM/temporal models) trained on historical AIS-derived arrivals, berth/crane throughput, and seasonality (day-of-week, peak season, holidays).
- Incorporate exogenous signals: weather/sea state, upstream port delays, labor actions, and known schedule bunching (multiple mega-vessels arriving together).
- Output both a point forecast and an uncertainty band, not a single number presented as fact.

### Validation / Technical Requirements
- Do not claim high forecast confidence when historical data for a terminal is sparse.
- Forecasts must be reproducible given the same inputs and model version — log the model version with every prediction.
- Re-forecast whenever a vessel ETA is revised or a berth/crane goes down unexpectedly.

---

## 9. Module G — Hotspot / Bottleneck Detector

### Functional Requirements
- Identify which resource is the binding constraint for a predicted delay: berth availability, crane throughput, yard space, or gate/truck capacity.
- Compute a composite Congestion Risk Score per terminal/zone from queue length, utilisation, throughput variance, and forecast confidence.
- Rank hotspots and mark the single most actionable one for the current shift.

### Validation / Technical Requirements
- The busiest berth is not always the true bottleneck — a downstream yard or gate constraint can be the real cause.
- Hotspot ranking must degrade gracefully (wider bands, lower confidence) when input data is incomplete rather than fail silently.

---

## 10. Module H — Anomaly & Disruption Detector

### Functional Requirements
- Detect abnormal patterns: sudden vessel bunching, equipment outage, labor shortage signals, weather closures.
- Use robust statistical methods or Isolation Forest against historical baselines for early warning.
- Distinguish a genuine operational disruption from a data-entry or sensor error before alerting.

### Validation / Technical Requirements
- Do not assert strong anomaly certainty with fewer than a minimum historical sample size for that terminal.
- Ask for human confirmation before an anomaly automatically triggers a re-plan.

---

## 11. Module I — Alternate Routing & Diversion Recommender

### Functional Requirements
- For carriers/vessels facing a predicted high-congestion window, recommend alternate berthing windows, alternate terminals within the port, or (where relevant) alternate nearby ports.
- Rank alternatives by expected time saved, additional distance/fuel cost, and feasibility (draft, service compatibility).
- Show the trade-off explicitly — an alternative that saves time but adds significant transit cost must not be hidden.

### Validation / Technical Requirements
- Respect hard constraints (a vessel too large for an alternate berth is not a valid recommendation).
- Do not recommend diversions based on a single noisy forecast point — require sustained predicted congestion above a threshold.

---

## 12. Module J — Berth Allocation & Crane Assignment Optimiser

### Functional Requirements
- Given the vessel schedule and forecasted congestion, produce a berth allocation plan and crane assignment plan for the planning horizon.
- Use a constraint-based/OR approach (e.g. mixed-integer programming or a metaheuristic such as genetic algorithm/tabu search) — this is the classical Berth Allocation Problem (BAP) and Quay Crane Assignment Problem (QCAP) from OR literature.
- Hard constraints: berth length/depth vs. vessel size/draft, crane availability, tidal windows, non-overlap of vessels on the same berth.
- Soft objectives: minimise total waiting time, minimise makespan, balance crane workload, respect carrier priority tiers.

### Validation / Technical Requirements
- Never produce a plan that violates a hard physical constraint, even if it improves the objective score.
- Re-optimise incrementally when a single vessel's ETA changes, rather than always recomputing from scratch (for demo responsiveness).
- Expose the objective weights used so a supervisor can understand why one plan was chosen over another.

---

## 13. Module K — 72-Hour Port Operations Plan Generator

### Functional Requirements
- Convert the optimiser's berth/crane assignments and the forecasted hotspots into a shift-by-shift operations plan document.
- Include: expected vessel arrivals, assigned berths/cranes, flagged risk windows, recommended pre-emptive actions (e.g. reposition cranes, open extra gate lanes).
- Use an LLM only to phrase this plan clearly for a human shift supervisor — the underlying numbers must come from modules F–J, not be generated by the LLM.

### Validation / Technical Requirements
- The plan must cite which forecast/optimisation run it was generated from, with a timestamp, for auditability.
- If confidence is low for part of the horizon, the plan must say so rather than presenting it with false certainty.

---

## 14. Module L — Scenario Simulator / What-If

### Functional Requirements
- Let a user simulate: an added/removed berth, a crane outage, a vessel bunching event, or a schedule change, and see the resulting congestion and plan impact.
- Compare baseline vs. scenario side-by-side on wait time, utilisation, and plan feasibility.
- Allow scenario cloning and rollback to baseline.

### Validation / Technical Requirements
- Prevent contradictory scenario parameters (e.g. a berth marked both closed and assigned) from being applied silently.

---

## 15. Module M — Recommendation Explainability

### Functional Requirements
- For every hotspot flag, routing suggestion, and berth/crane assignment, show the contributing evidence (forecasted queue length, utilisation, constraint that bound the decision).
- Display confidence and the key assumptions behind each number.

### Validation / Technical Requirements
- Avoid unsupported causal language ("X caused the delay") when only correlation/contribution can be shown.
- If evidence is weak or data is sparse, say so explicitly rather than smoothing over uncertainty.

---

## 16. Module N — Dashboard & Visualisation

### Functional Requirements
- KPI cards: current/forecasted queue length, average berth wait, yard utilisation, top hotspot, plan risk level.
- Visuals: congestion heatmap by terminal/zone, 72-hour Gantt of berth/crane assignments, arrival timeline, before/after scenario comparison.
- Drill-down from port → terminal → berth → individual vessel.

### Validation / Technical Requirements
- Keep the primary dashboard action-oriented for a shift supervisor; push deep analytics to a secondary view.
- Do not use colour alone to indicate severity (accessibility).

---

## 17. Core Calculation Logic

**Suggested Congestion Risk Score:**
w₁(Forecasted Queue Length) + w₂(Utilisation Ratio) + w₃(Throughput Variance) + w₄(Forecast Uncertainty) + w₅(Disruption Signal)

**Suggested Berth/Crane Assignment Objective:**
minimise [ α·Total Vessel Wait Time + β·Makespan + γ·Crane Workload Imbalance − δ·Carrier Priority Bonus ], subject to draft/length/tide/crane hard constraints

---

## 18. Recommended Database Design

*Core entity flow: Terminal → Berth/Crane/YardZone → VesselCall (schedule) → AISTrack/CongestionObservation → ForecastRun → HotspotFlag → BerthCraneAssignment → OperationsPlan → Scenario → ImpactAssessment*

---

## 19. Recommended Technical Architecture

*React/Next.js Dashboard → FastAPI backend → Forecasting Service (time-series ML) + Optimisation Service (OR-Tools/MIP solver) + Rules/Constraint Engine → PostgreSQL + TimescaleDB (for AIS time-series) → Vessel Schedule & Emission-Factor-style Reference Data Stores*

---

## 20. Winning Hybrid AI Architecture

- Vessel Schedule & Capacity Data
- Validation & Normalisation Engine
- AIS/Historical Congestion Store
- Forecasting Engine (ML) + Anomaly Detector
- Hotspot Ranker
- Berth/Crane Optimiser (OR/MIP)
- Scenario Simulator
- Explainable LLM Layer
- 72-Hour Plan + Dashboard

**Why hybrid is better:** Forecasting is probabilistic and benefits from ML; berth/crane assignment is a hard-constraint scheduling problem best solved deterministically with OR methods so plans are always physically valid; the LLM only turns validated numbers into a readable plan and explanation, never invents scheduling truth.

---

## 21. Hero Feature — Congestion Heatmap & 72-Hour Berth Gantt

Example drill-down: Terminal 2 shows a forecasted 68% congestion risk for the next 36 hours. Root causes: three post-panamax vessels arriving within an 8-hour window (bunching) and one crane under maintenance. Best action: stagger berth windows for two of the three vessels and reassign one crane from Terminal 1. Show expected wait-time reduction, affected vessels, and confidence.

---

## 22. Critical Edge Cases

- Two vessels with overlapping ETAs and identical berth requirements (only one berth available).
- A vessel's declared ETA and AIS-derived ETA disagree by more than a defined threshold.
- A crane or berth goes down mid-plan — the optimiser must re-plan without violating constraints for vessels already berthed.
- Severe weather forces a full terminal closure for an unknown duration.
- New terminal or berth with no historical baseline — forecasting confidence must be explicitly low.
- A carrier requests priority berthing that would violate fairness or contractual rules for another carrier.
- Data feed outage (AIS or terminal operating system) during a live demo — system must degrade to last-known-good state, not crash or fabricate data.

---

## 23. Winning Solution Differentiators

- Predicts before congestion happens, using forecasting + optimisation, not just a live status dashboard.
- Berth/crane plans are always physically valid because they come from a constraint solver, not an LLM guess.
- Every hotspot and recommendation is explainable back to underlying data.
- Produces an artifact a shift supervisor can actually act on: a 72-hour plan, not just charts.

---

## 24. Suggested Hackathon MVP Scope

**Must implement:** Modules A, B, C (with a realistic synthetic/sample dataset), D, F (simplified forecasting model), G, J (simplified BAP/QCAP solver), K, and N, with the Congestion Heatmap and 72-hour Gantt as the presentation centerpiece.

**Phase 2 / future:** Live AIS feed ingestion, full anomaly-detection module (H), multi-port alternate routing (I), scenario simulator (L) beyond one or two cases, and continuously-learning forecasting models.

---

## 25. Recommended Demo Scenario

Use a fabricated but realistic mid-size container terminal modelled loosely on LA/Long Beach scale-down data:

- 6 berths, 12 quay cranes, 4 yard zones, 1 gate complex.
- A 5-day synthetic vessel call schedule with a deliberate bunching event (3 vessels within 10 hours) on day 3.

Expected narrative: system forecasts a congestion spike 24 hours before the bunching event, flags Berth 3–4 and the yard as the binding constraints, recommends staggering two vessels and reassigning a crane, then shows the 72-hour plan and the baseline-vs-optimised wait-time comparison.

---

## 26. Suggested Student Team Split

- **Data & Ingestion:** schedule/AIS ingestion, normalisation, synthetic data generation.
- **Forecasting:** time-series congestion model, anomaly detection.
- **Optimisation:** berth allocation / crane assignment solver (OR-Tools or similar).
- **Product/Frontend:** dashboard, heatmap, 72-hour Gantt, scenario simulator UI.
- **Integration & Explainability:** LLM plan-narrative layer, explainability surfacing, demo script.

---

## 27. Final Pitch Message

> "We don't just show you today's congestion — we predict tomorrow's, tell you exactly which resource will bottleneck, and hand your shift supervisor a physically valid 72-hour plan to prevent it."

---

## 28. Reference Frameworks / Data Sources to Use

- NOAA/BOEM MarineCadastre AIS data (AccessAIS + bulk GeoParquet) — vessel-track ground truth for arrivals, dwell time, and congestion baselines.
- U.S. BTS Port Performance Freight Statistics Program — weekly vessel berthing statistics, TEU throughput, top-25-port capacity data for validation and benchmarking.
- Academic AIS-based berth/queue studies (e.g. Maher Terminal, Port of Houston queue behaviour) — for realistic queuing parameters and model validation.
- Berth Allocation Problem (BAP) / Quay Crane Assignment Problem (QCAP) OR literature — for the optimisation formulation and constraints.

*See the companion Dataset & Data Sources Research document for full detail, links, and an acquisition plan.*

---

## 29. Implementation Acceptance Checklist

- [ ] Terminal, berth, crane and yard data can be entered/edited and validated.
- [ ] Vessel schedule can be ingested (manual/CSV) with ETA revision history retained.
- [ ] Units and timestamps are normalised consistently across all sources.
- [ ] Historical AIS/congestion baselines are stored and versioned.
- [ ] Congestion forecasts are reproducible and carry an explicit confidence band.
- [ ] Top hotspots are ranked, attributed to a specific resource, and explainable.
- [ ] Berth/crane assignment plan never violates a hard physical constraint.
- [ ] 72-hour operations plan is generated with visible assumptions and confidence.
- [ ] At least one what-if scenario can be compared against baseline.
- [ ] Dashboard displays an actionable congestion heatmap and berth/crane Gantt.
- [ ] Critical edge cases (Section 22) do not produce misleading or invalid output.
- [ ] Every forecast/plan retains its model version and generation timestamp for traceability.
