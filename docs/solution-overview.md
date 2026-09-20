# Solution Overview — PortPulse AI

A FastAPI gateway over five capability services, a SimPy synthetic operations layer, PostgreSQL
persistence, and a React/Vite dashboard. Everything shares one model time `t0` from `context.py`.

```
REAL POLB capacity + SimPy operations layer  ──►  PostgreSQL
                                                   │
                                                   ▼
                              context.py ──► EngineContext (one t0)
                                                   │
        ┌──────────────────────────────────────────┼───────────────────────────┐
        ▼                      ▼                    ▼                          ▼
 ① forecasting.py      ② anomaly.py         ③ hotspot.py                ④ optimiser.py
 (LightGBM + bands)  (Isolation Forest)  (risk score + binding)   (OR-Tools CP-SAT BAP/QCAP)
        │                                                                    │
        └──────────────► ⑤ routing.py ──► ⑥ plan.py ──► llm.py (Bob) ◄────┘
                                                   │
                                                   ▼
                                   pipeline.py ──► FastAPI /api/* ──► React dashboard + Bob
```

---

## ⓪ Simulation & data — `services/simulation.py`, `reference.py`, `seed.py`, `pipelines/ais_generate.py`

**REAL:** the Port of Long Beach terminal table (berth lengths, deepsea berths, STS cranes, LBCT 3.5 M TEU)
is hard-coded from POLB terminal fact sheets and becomes the optimiser's hard constraints.

**Vessel queue (SimPy):** a **SimPy** discrete-event simulation generates the vessel-call schedule and ETA
revision history. Each berth is a `simpy.Resource(capacity=1)`; vessels wait in an observable anchorage
queue, work for `moves / (cranes × rate) + buffer` hours, release the berth, fill the yard and drain
through the gate. Deterministic given seed `20240817`.

**AIS congestion history (`source="DEMO_AIS"`):** The empty-database seed loads a realistic 14-day
NOAA AccessAIS-format position record set via `pipelines/ais_generate.py`, runs it through the
`ais.build` congestion-series stage, and loads it labelled `DEMO_AIS` — a label the UI surfaces
wherever synthetic data is displayed. The Quality page exposes a
**Regenerate AIS** button for on-demand refresh. A real NOAA AccessAIS export can replace this at any
time with two shell commands (see `docs/setup-guide.md §5`).

---

## ① Forecasting — `services/forecasting.py` (LightGBM + quantile bands)

**Targets:** congestion index, queue length, average anchorage wait, **yard utilisation** — at 24/48/72 h.
**Features:** lag/rolling congestion, calendar terms (hour-of-day, day-of-week), **ETA arrival pressure**
(bunching), berth load factor, yard utilisation.
**Model:** **LightGBM** point regressor per zone/target + **quantile regression (α = 0.1 / 0.9)** for the
80 % band ("almost for free"). A recursive 1-step rollout produces the horizon.
**Validation:** 48 h holdout (MAE / R² / skill vs persistence) + multi-origin rollouts → per-horizon
MAE / σ / bias buckets. Every run carries a **model version** logged with the predictions.
**Drivers:** arrival surge, sustained queue pressure, diurnal window, service catch-up.

## ② Anomaly detection — `services/anomaly.py` (sklearn Isolation Forest)

Per-zone Isolation Forest over a 7-feature window (index, queue, wait, yard, Δqueue, Δindex, rolling σ).
Classifies **BUNCHING / OUTAGE / YARD_SATURATION / VARIANCE** and separates a likely **DATA_ERROR**
(implausible jump) from a genuine disruption. Refuses to assert below `MIN_SAMPLES = 96 h`.

## ③ Hotspot / bottleneck — `services/hotspot.py`

Composite risk score (doc §17):
`risk = 100 · (w1·queue + w2·utilisation + w3·variance + w4·uncertainty + w5·disruption)`.
`utilisation` is the **maximum resource pressure** across BERTH / CRANE / YARD / GATE — so the module names
the *binding* resource, not just the busiest berth. Confidence degrades with sparse data or unresolved rows.

## ④ Berth & crane optimiser — `services/optimiser.py` (Google OR-Tools **CP-SAT**)

**Formulation (BAP/QCAP).** Decision variables: berth assignment, crane count (2…min(berth max, 8)) and
start time per vessel; **optional fixed-size intervals** per (vessel, berth, crane-count).
**Hard constraints:** `LOA ≤ berth length`, `draft ≤ berth depth`, `beam ≤ crane reach`; `AddNoOverlap`
per berth; `AddCumulative` per terminal so simultaneous cranes ≤ the available crane pool; a vessel must
*start* within the 72 h horizon or it is deferred.
**Objective (exposed weights):** `α·priority-weighted wait + β·makespan + γ·crane-use − δ·throughput`,
throughput = vessels served. A **FIFO first-fit baseline** is solved alongside for measured deltas.
**Verified:** CP-SAT returns `OPTIMAL`/`FEASIBLE`; on the seeded instance it improves total wait (~−19 %)
and makespan (~−55 h) vs FIFO at equal service count; ~0.3–8 s, cached.

## ⑤ Alternate routing — `services/routing.py`

DIVERT / SLOW_STEAM / PRIORITY_WINDOW / HOLD, using the forecast wait at the vessel's zone (or 78 h if
unscheduled). **Sustained-congestion requirement** (≥ 3 consecutive forecast hours above threshold) before
recommending a divert. Documented cost model: `$32k/day` ship operating cost, `$180`/reefer spoilage risk,
alt-port table (Oakland / Seattle-Tacoma / Prince Rupert / Ensenada) with availability buffers.

## ⑥ 72-hour plan — `services/plan.py` + `llm.py`

12 × 6 h shifts with arrivals, berthings, crane deployment, congestion alerts (WATCH ≥45 / WARN ≥60 /
CRIT ≥75), routing decide-by deadlines and a supervisor checklist; emits JSON + printable text and cites
the **forecast/optimiser run ids + model version**. The **Bob** agent rewrites it for a supervisor —
strictly from the given numbers — with a deterministic fallback when the Bob agent is unavailable.

## Bob — load-bearing assistant — `routers/bob.py` + `services/llm.py`

`POST /api/bob` → intent detection → the matching pack **actually runs the engines** → engine JSON becomes
an `ENGINE DATA` block → the Bob agent answers strictly from it → the reply is persisted with the `actions` it ran
and `mode` (`llm` | `deterministic`).

---

## Key constants (documented)

| Constant | Value | Used by |
|---|---|---|
| STS productivity | 28 moves/crane-hour | optimiser |
| Ship operating cost | $32,000/day | routing, overview |
| Reefer spoilage risk | $180/unit | routing |
| Congestion index | `clamp(60·(queue/20) + 40·(wait/72), 0, 100)` | everywhere |
| Berth turnaround | ~36 h | forecast inflow |
| Risk weights w1..w5 | 0.34 / 0.24 / 0.16 / 0.16 / 0.10 | hotspot |
| Alert levels | WATCH 45, WARN 60, CRIT 75 | plan, overview |

**Terminal capacity — real, cited:** Port of Long Beach terminal fact sheets. **Vessel queue —
SimPy-generated, stored in `vessel_call` table. Congestion history — realistic AIS-format pipeline,
`source="DEMO_AIS"`, refreshable from the Quality page.**
