# TEAM_PLAN — 4-Way Parallel Work Plan

**Goal:** finish PortFlow SBX with 4 people coding **in parallel** and merging **cleanly** (no
"works-on-my-machine" pile-up). The doc is built so that **no two people edit the same file**, and every
cross-team dependency is a **frozen contract** agreed before anyone starts.

Current status (what's done / not): [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md).
Architecture & interfaces: [`docs/architecture.md`](docs/architecture.md) · [`docs/bob-mcp.md`](docs/bob-mcp.md).

---

## 0. TL;DR — how conflicts are avoided

| Rule | Why it matters |
|---|---|
| **R0. Phase 0 freeze first (≈3 h, everyone)** | We commit the *interfaces* (DB columns, API routes, TS types, test harness) **before** splitting. Parallel code then compiles against stubs instead of colliding. |
| **R1. One owner per file** | Each file has exactly one owner (matrix in §4). If you need a change in someone else's file, you open a tiny PR **to them** — you don't edit it. |
| **R2. Shared files are Integrator-only** | `models.py`, `main.py`, `reference.py`, `serialize.py`, `pipeline.py`, `mcp_server.py`, `docs/*` → **Integrator (Lead)** only. |
| **R3. Feature flags for partial merges** | New behaviour is behind `FEATURE_*` env flags (default **off**), so a half-finished branch can merge without breaking `main`. |
| **R4. Contract tests gate every merge** | `tests/test_contracts.py` + `npm run build` must pass before merge. Response shapes are asserted, so a backend change that breaks the UI fails in CI, not at the demo. |
| **R5. Fixed merge order + integration window** | W1 → W2 → W3 → W4, then a shared integration block. Never merge W2 before W1's schema lands. |

---

## 1. Current state (1-minute snapshot)

**Done & running:** SimPy simulation · LightGBM forecast (+quantile bands, validation) · IsolationForest
anomalies · hotspot risk score + binding resource · **OR-Tools CP-SAT** BAP/QCAP + FIFO baseline ·
routing · 72h plan · FastAPI (12 routes) · PostgreSQL persistence · React/Vite dashboard (6 tabs) ·
**MCP server for IBM Bob (11 tools)** · AIS pipeline.

**Remaining (from `IMPLEMENTATION_STATUS.md` §6):**

| # | Gap | Module | Owner in this plan |
|---|---|---|---|
| P0-1 | Unit normalisation + per-terminal data-completeness score | D | **W1** |
| P0-2 | True congestion heatmap + port→terminal→berth→vessel drill-down + scenario-compare view | N | **W4** |
| P0-3 | CSV/EDI schedule upload + re-plan on ETA revision | B | **W1** (+W3 re-plan hook) |
| P1-4 | Weather pipeline (Open-Meteo) into forecast + anomalies; BTS benchmark | — | **W1** (pipeline) + **W2** (features) |
| P1-5 | Alternate in-port terminals / berthing windows | I | **W3** |
| P1-6 | Scenario expansion (berth add/remove, bunching) + clone/rollback | L | **W3** |
| P1-7 | Tidal windows; incremental warm-start re-optimise | J | **W3** |
| — | Submission: demo video, screenshots, team details, Bob registration | — | **W4** |

---

## 2. Phase 0 — Interface Freeze — ✅ **DONE**

> Committed on `main`. **Start your workstream from this commit — do not re-do Phase 0.**
> If you need a change to a frozen interface, ask the Integrator (additive only).

**What is now on `main`:**

| Phase-0 item | Status | Where |
|---|---|---|
| New DB tables + columns | ✅ applied to PostgreSQL | `app/models.py`, `app/db.py::ensure_schema()` (`ADD COLUMN IF NOT EXISTS`, non-destructive) |
| New tables | ✅ `weather_observation`, `terminal_quality`, `tidal_window`, `vessel_schedule_upload` | `app/models.py` |
| Frozen API stubs | ✅ all return the documented shape with `stub: true` | `routers/quality.py`, `routers/anomalies.py`, `routers/scenarios.py`, `routers/catalog.py` (`/api/vessels/upload`) |
| Frozen keys on existing routes | ✅ `forecast.weather_used/confidence`, `optimise.tidal_feasible/incremental`, `plan.summary.confidence_by_bucket` | `routers/forecast.py`, `optimise.py`, `plan.py` |
| Anomalies moved to its own router | ✅ | `routers/anomalies.py` |
| Scenario endpoints moved out of `optimise.py` | ✅ | `routers/scenarios.py` |
| Frontend split into files | ✅ 6 tabs + `components/ui.tsx` + `types.ts` | `src/frontend/src/` |
| Feature flags | ✅ all default `false` | `app/config.py`, `.env.example` |
| Tests + merge gate | ✅ **13 passing** (`uv run pytest -q`), `npm run build` green | `tests/contracts*.py`, `tests/engines.py` |
| Frozen API contract doc | ✅ | [`docs/api-contract.md`](docs/api-contract.md) |

**You can start now:** each workstream edits only its own files (matrix §4) and implements the logic behind the
stubbed endpoint / flag it owns. Pull `main`, branch, code, run `uv run pytest tests/ -q` (+ `npm run build` for W4).

---

### (Reference) what Phase 0 froze — for the record

**Old heading kept for context; all of the below is already committed.**

**P0.1 — DB schema freeze** *(Integrator commits)* — add to `src/backend/app/models.py`:

| Model | Change | Consumed by |
|---|---|---|
| `WeatherObservation` **(new)** | `ts, hours_ago, wind_kn, gust_kn, wave_m, visibility_km, source, confidence` | W2 |
| `TerminalQuality` **(new)** | `terminal_id, observed_at, completeness_pct, missing_json, rules_version` | W1/W4 |
| `TidalWindow` **(new)** | `berth_id, ts, min_depth_ft, note` | W3 |
| `VesselScheduleUpload` **(new)** | `uploaded_at, filename, rows, accepted, rejected, report_json` | W1 |
| `VesselCall` | **+** `voyage_number` (dedupe key), `normalised` (JSONB: original→SI units) | W1/W3 |
| `Scenario` | **+** `parent_scenario_id`, `status` (`DRAFT/APPLIED/ROLLED_BACK`) | W3 |
| `RoutingRecommendation` | **+** `option_detail` (JSONB: in-port terminal/window) | W3 |
| `ForecastRun` | **+** `data_version`, `feature_flags` (JSONB) | W2 |
| `OperationsPlan` | **+** `confidence_json` (per-horizon) | W3 |

Then `uv run python -c "from app.db import init_db; init_db()"` (additive, safe).

**P0.2 — API contract freeze** *(Integrator writes `docs/api-contract.md`; owners add stubs)* — every new
route returns the frozen shape (may return `501`/empty until implemented):

| Method | Path | Owner | Frozen response keys |
|---|---|---|---|
| GET | `/api/quality` | W1 | `{terminals:[{code, completeness_pct, missing:[]}], rules_version}` |
| GET | `/api/weather?hours=72` | W1 | `{points:[{hour, ts, wind_kn, wave_m}], source}` |
| POST | `/api/vessels/upload` | W1 | `{accepted, rejected, errors:[], revisions_created}` |
| GET | `/api/forecast?zone=` | W2 | existing **+** `weather_used: bool`, `confidence: 0..1` |
| GET | `/api/anomalies` | W2 | `{anomalies:[…]}` *(moves out of `catalog.py`)* |
| POST | `/api/optimise` | W3 | existing **+** `tidal_feasible: bool`, `incremental: bool` |
| POST | `/api/scenarios` | W3 | existing **+** `scenario_id`, `kind` |
| POST | `/api/scenarios/extended` | W3 | `{baseline, scenario, impact, feasible}` |
| POST | `/api/scenarios/{id}/rollback` | W3 | `{restored: true}` |
| GET | `/api/plan?confidence=1` | W3 | existing **+** `summary.confidence_by_bucket` |

**P0.3 — Frontend freeze** *(W4)* — split the 700-line `App.tsx` into files **before** adding features:

```
src/frontend/src/
├── App.tsx                 # shell + tab nav ONLY
├── api.ts                  # typed client (add stubs for all new endpoints)
├── types.ts                # shared TS types mirroring the API contract
├── components/ui.tsx       # Card, Kpi, Level, Sparkline, useAsync (shared atoms)
└── tabs/
    ├── Overview.tsx  Forecast.tsx  BerthCranes.tsx
    ├── Routing.tsx   Plan.tsx      Bob.tsx
    └── index.ts
```
After this, **W4 owns every file in `tabs/`** and no one else edits them.

**P0.4 — Test + flag harness** *(Integrator)*
- `src/backend/tests/test_contracts.py` — asserts each endpoint's response **keys** (not values) match §P0.2.
- `src/backend/tests/test_engines.py` — smoke: seed → `build_full` → assert `solver=="ortools-cp-sat"` and forecast points == 72.
- `FEATURE_*` flags added to `config.py` (default `false`).
- Add `pytest` to `pyproject.toml` dev deps; document `uv run pytest tests/ -q`.

**Phase 0 exit criteria:** ✅ met — new models + route stubs + split frontend + tests all on `main`;
`uv run pytest -q` green; `npm run build` green; `docs/api-contract.md` committed.

---

## 3. The 4 workstreams

### W1 — Data & Ingestion *(backend data layer)* — **Module D + B + weather/BTS**
**Owns:** `services/simulation.py`, `services/context.py`, `services/dataquality.py` **(new)**,
`seed.py`, `pipelines/weather.py` **(new)**, `pipelines/bts.py` **(new)**, `pipelines/schedule.py` **(new)**,
`routers/catalog.py`, `routers/quality.py` **(new)**

Tasks
1. **Normalisation engine** (`dataquality.py`): canonical units (TEU, ft↔m, UTC), keep `original`↔`normalised`, versioned rule set; write into `VesselCall.normalised`.
2. **Data-completeness score** per terminal → `TerminalQuality`; expose `GET /api/quality`; feed it into hotspot confidence (coordinate with W2 via the frozen key).
3. **Weather pipeline** (`pipelines/weather.py`): Open-Meteo historical+forecast for `REFERENCE_LAT/LON` → `WeatherObservation` (with a cached snapshot fallback if the API is down).
4. **BTS benchmark** (`pipelines/bts.py`): load PPFSP weekly berthing stats → validation table (no UI).
5. **CSV schedule upload** (`routers/catalog.py` `POST /api/vessels/upload` + `pipelines/schedule.py`): parse, dedupe on `IMO+voyage_number`, write `EtaRevision` rows, flag `unresolved` instead of defaulting.

**Acceptance:** `GET /api/quality` returns all 4 terminals with a score; weather rows exist for 72h; a sample
CSV upload creates revisions and is idempotent; `pytest tests/test_contracts.py` green.

---

### W2 — Forecasting · Anomaly · Hotspot *(backend ML)* — **Modules F/G/H**
**Owns:** `services/forecasting.py`, `services/anomaly.py`, `services/hotspot.py`,
`routers/forecast.py`, `routers/anomalies.py` **(new, moved out of catalog.py)**

Tasks
1. **Weather features** in LightGBM (wind/gust/wave) behind `FEATURE_WEATHER`; expose `weather_used`.
2. **Model registry**: `model_version` + `data_version` + `feature_flags` on every `ForecastRun`; store metrics.
3. **Low-confidence path**: when a terminal's completeness score (from W1) or history length is low, widen bands and lower `confidence` (never silently confident).
4. **Anomaly upgrade**: add weather signals; keep `DATA_ERROR` vs disruption distinction; own `/api/anomalies`.
5. **Per-horizon confidence** exposed on the forecast (consumed by W3's plan via the frozen key).

**Acceptance:** `/api/forecast` includes `weather_used` + `confidence`; `pytest` green; skill-vs-persistence
recorded in the model card; sparse-data case returns a visibly lower confidence.

---

### W3 — Optimiser · Routing · Plan · Scenarios *(backend OR + decisions)* — **Modules I/J/K/L**
**Owns:** `services/optimiser.py`, `services/routing.py`, `services/plan.py`,
`routers/optimise.py`, `routers/routing.py`, `routers/plan.py`, `routers/scenarios.py` **(new, absorbs the scenario endpoint out of optimise.py)**

Tasks
1. **Tidal windows**: read `TidalWindow`, add a time-varying depth constraint to the CP-SAT model; expose `tidal_feasible`.
2. **Incremental warm-start**: `POST /api/optimise?incremental=1` → hint CP-SAT with the previous solution (`AddHint`) instead of cold-start; expose `incremental`.
3. **In-port alternates** in routing: add alternate POLB terminal / berthing-window options to `option_detail` (keep the sustained-congestion rule).
4. **Scenario expansion** (`routers/scenarios.py`): berth add/remove, crane outage, **bunching event**, schedule change; `POST /api/scenarios/extended`, `POST /api/scenarios/{id}/rollback`, clone via `parent_scenario_id`.
5. **Plan provenance + confidence**: cite run ids + model version; add `summary.confidence_by_bucket`.

**Acceptance:** tidal constraint never violated (assert in tests); incremental solve faster than cold start;
extended scenarios return baseline-vs-scenario deltas; rollback restores baseline; `pytest` green.

---

### W4 — Frontend · Demo · Submission — **Module N + deliverables**
**Owns:** `frontend/src/**`, `demo/**`, `presentation/**`

Tasks
1. **Phase 0 tab split** (do first, see P0.3).
2. **Congestion heatmap** (`tabs/Forecast.tsx` or a new `components/HeatmapGrid.tsx`): zone × hour matrix, colour **+ text/icon** (accessibility: never colour alone).
3. **Drill-down** (`components/DrillDownDrawer.tsx`): port → terminal → berth → vessel.
4. **Scenario-compare view** (`components/ScenarioCompare.tsx`): baseline vs scenario side-by-side, wired to `/api/scenarios/extended`, with clone/rollback buttons.
5. **Schedule upload + quality panel** (`components/ScheduleUpload.tsx`, `tabs/Overview.tsx` quality card) wired to `/api/vessels/upload` + `/api/quality`.
6. **Submission**: refresh screenshots, record the demo video per `demo/demo-video-script.md`, update team details.

**Acceptance:** `npm run build` green; every new view reads a real endpoint (no hard-coded data); heatmap and
drill-down work keyboard-only; screenshots + video link updated.

---

## 4. File-ownership matrix (the anti-conflict map)

| Area / file | Owner | Rule |
|---|---|---|
| `app/models.py` | **Integrator** | freeze in P0; changes via Integrator only |
| `app/main.py`, `app/reference.py`, `app/serialize.py`, `app/config.py` | **Integrator** | shared; PR to Integrator |
| `app/services/pipeline.py` | **Integrator** | orchestration; PR to Integrator |
| `app/mcp_server.py` | **Integrator** | expose new tools only after W-track merges |
| `app/services/simulation.py`, `context.py`, `dataquality.py`, `seed.py` | **W1** | exclusive |
| `app/pipelines/*`, `app/routers/catalog.py`, `app/routers/quality.py` | **W1** | exclusive |
| `app/services/forecasting.py`, `anomaly.py`, `hotspot.py` | **W2** | exclusive |
| `app/routers/forecast.py`, `app/routers/anomalies.py` | **W2** | exclusive |
| `app/services/optimiser.py`, `routing.py`, `plan.py` | **W3** | exclusive |
| `app/routers/optimise.py`, `routing.py`, `plan.py`, `scenarios.py` | **W3** | exclusive |
| `frontend/src/**` | **W4** | exclusive |
| `demo/**`, `presentation/**` | **W4** | exclusive |
| `docs/*` (except this plan & `api-contract.md`) | **Integrator** | PR to Integrator |
| `TEAM_PLAN.md`, `docs/api-contract.md` | **Integrator** | single writer |

> ⚠️ `app/routers/optimise.py` currently holds the scenario endpoint — W3 **moves it** to `routers/scenarios.py`
> in their first commit (Integrator does not register the old path until then).

---

## 5. Merge & integration protocol

**Branches:** `feat/w1-data`, `feat/w2-ml`, `feat/w3-opt`, `feat/w4-ui`.

**Daily loop (each person):**
```bash
git checkout main && git pull
git checkout feat/wX-... && git rebase main        # resolve in YOUR files only
uv run pytest tests/ -q        # backend
npm run build                  # frontend (W4)
git push --force-with-lease
```

**Merge order (Integrator):** **W1 → W2 → W3 → W4.**
Reason: W1 lands the data/columns W2/W3 read; W4 renders what W1–W3 expose. Contract stubs mean W2–W4 can
*already* be coded before W1 merges — they just aren't switched on.

**Feature flags (default off) so partial merges don't break `main`:**
`FEATURE_WEATHER`, `FEATURE_QUALITY`, `FEATURE_TIDAL`, `FEATURE_INCREMENTAL`, `FEATURE_SCENARIOS_EXT`,
`FEATURE_UPLOAD`. Each owner flips their flag on **in the same PR that completes the feature**.

**CI gate (add to `.github/workflows/`):** backend `uv run pytest tests/ -q`; frontend `npm ci && npm run build`.

**Integration window (last ~3 h):** Integrator + one other person run the full stack
(`seed → uvicorn → npm run dev`), click every tab, hit every endpoint, then re-record screenshots.

---

## 6. Suggested timeline (2 days, 4 people)

| Slot | W1 Data | W2 ML | W3 OR/decisions | W4 Frontend |
|---|---|---|---|---|
| **Day 0** | **Phase 0 freeze — everyone** (models · API contract · tab split · tests) | | | |
| Day 1 AM | normalisation + quality | weather features + model registry | tidal windows | tab split polish + heatmap |
| Day 1 PM | weather pipeline | anomaly upgrade + confidence | incremental warm-start | drill-down |
| Day 2 AM | CSV upload + BTS | hotspot confidence wiring | scenarios (berth/bunching/rollback) | scenario-compare + upload/quality UI |
| Day 2 PM | **integration + demo** (Integrator) | | | screenshots + video |

---

## 7. Definition of Done (per workstream)

- [ ] Feature works end-to-end against the **real** DB/API (no mock data in shipped paths).
- [ ] `uv run pytest tests/ -q` green (backend) / `npm run build` green (frontend).
- [ ] Contract test for any new/changed endpoint shape.
- [ ] Feature flag flipped **on** in `.env.example` with a comment.
- [ ] Numbers documented where they’re constants (`reference.py`), not inline.
- [ ] Data honesty preserved: REAL POLB capacity stays cited; synthetic data stays labelled `DEMO_AIS`.
- [ ] `IMPLEMENTATION_STATUS.md` row updated (Integrator) — 🟡 → ✅.

---

## 8. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Two people edit `models.py` / `App.tsx` | High without P0 | P0 freeze + ownership matrix; only Integrator/W4 touch them |
| W2 codes against a column W1 renamed | Medium | columns frozen in P0; contract test asserts response keys |
| Frontend breaks when backend changes a key | Medium | `api-contract.md` + `test_contracts.py` + `npm run build` gate |
| CP-SAT solve time grows with tidal constraints | Medium | keep `max_time_in_seconds`, add warm-start hints (W3), cache |
| Weather API down during demo | Medium | W1 caches a snapshot; forecast works with `weather_used=false` |
| Scope creep (P2 items) | Medium | P2 is explicitly **out of scope** this sprint |
| Demo-day “merge surprise” | Low with gates | integration window + feature flags + contract tests |

---

## 9. Assign slots (fill in names)

| Workstream | Owner | Backup / reviewer |
|---|---|---|
| **Integrator** (Phase 0, shared files, merges, `models.py`, MCP) | | |
| **W1** Data & Ingestion | | |
| **W2** Forecasting / Anomaly / Hotspot | | |
| **W3** Optimiser / Routing / Plan / Scenarios | | |
| **W4** Frontend / Demo / Submission | | |

**Rule of thumb:** if two people ever need the *same* file, the file gets a single owner and the other person
sends a patch. That one rule, plus Phase 0, is what keeps the merge clean.
