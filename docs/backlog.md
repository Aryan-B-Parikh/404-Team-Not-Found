# Backlog — tracked findings from audits & playtests

Process rule (audit rec #1): **every audit finding becomes an entry here with an
acceptance criterion, and passes close entries instead of re-deriving them.**
Move closed items to "Closed" with the commit/test that proves it.

Legend: 🔴 blocks a headline claim · 🟡 degrades UX or costs future changes · 🟢 hardening

## Open

(none — all shipped items are closed below)

## Recently closed

### B-10 Visual-density pass shipped (tiered pages) 🟢 — done 2026-09-20
3-tier layout applied without removing any data: BerthCranes = headline wait-delta vs FIFO
(−64.7h live) + 4 compact KPIs + always-visible Gantt + tabbed tier-3 (CP-SAT-vs-FIFO table /
assignments & deferred reasons / terminal capacity); Forecast = model card + per-horizon
validation behind "Model details & accuracy" collapsible (MAE/R² badge on the summary line);
Plan = shifts 01–02 visible, "Remaining shifts (10 of 12) · +27 planned movements" collapsible;
Routing = top-8 recommendation cards + "Show all 45" toggle. DEMO_AIS provenance and headline
improvement/confidence numbers stay tier-1 everywhere. New `ui/Collapsible.tsx` primitive;
sparklines deliberately skipped — every existing chart is primary content, not trend-only.
Verified live: tabs switch, collapsibles expand, build + typecheck green.
**Extension (same day, item-5/6 sweep):** Overview anomaly table collapsed behind
"Isolation Forest anomalies · N flagged of M" summary; **honesty fix — ScenarioTimeline's
"shift trajectory" chart was fabricated** (Math.sin interpolation from 4 real totals presented
as "derived from CP-SAT", plus a fake 2,000-move quota line): replaced with a grouped bar chart
of the real solver totals, captioned "solver-level totals only". QualityPage left as-is
(admin tools page — panels are destinations, not passive data) and CongestionMap left as-is
(all zones on a map is the correct density).

### B-3 Tabs are not deep-linkable 🟡 — CLOSED 2026-09-20
Raised by: playtest — `/forecast` URL lands on Overview; browser back/forward do nothing.
Closed: tab lives in the URL path (`App.tsx` — `tabFromPath`/`pushState`/`popstate`, `/` =
overview). Production serving via a FastAPI SPA fallback (`main.py` `spa_fallback`: real files
pass through, everything else gets `index.html`; Vite dev fallback covers dev). Proven live:
`curl /berth` → index.html shell, asset → 200, e2e `unknown deep link falls back to Overview` ✓.

### B-4 Simulator draws extreme congestion states on common seeds 🟡 — CLOSED 2026-09-20
Raised by: playtest — fresh seed drew port index 100, berth util 97.9%, CRIT alert.
Closed: measured 5 seeds (3/5 pinned at index 100), swept `DEMAND_BASE_GAP_HOURS` empirically
(4.6 → 100 · 6.5 → 36.8 · **5.4 → median 62.5**, berth util ≤ 61.2%); applied + regression test
`tests/test_sim_calibration.py` pins the acceptance criteria; dev DB reseeded so the live demo
shows the calibrated state.

### B-5 `GET /api/quality` performs writes on every read 🟡 — CLOSED 2026-09-19
Raised by: audit (B14 pattern reintroduced) — `NormalisationEngine.run()` + commit on GET.
**Acceptance:** `/api/quality` reads persisted state; normalisation runs only via an explicit
refresh action (POST) or the pipeline; two consecutive GETs return identical bodies with no new rows.

### B-6 `forecasting.py` still owns too many concerns 🟢 — CLOSED 2026-09-19
Raised by: audits 1–3. Closed in two steps: model cache → `services/model_cache.py`,
weather load/severity/adjustment → `services/weather_adjust.py` (729 → 594 lines); then the
orchestration split — `pipeline.py` (173 → 132 lines, sequencing only) delegates to
`services/persistence.py` (all engine-run writes), `services/overview.py` (dashboard projection),
`services/run_cache.py` (one thread-safe TTL idiom replacing two hand-rolled globals, one of them
racy). Public API preserved via re-exports; only internal test seams changed
(`pipeline._fc_cache.clear()`).

### B-7 Full OpenAPI → TypeScript contract generation 🟢
Raised by: audit — two contract owners (backend dataclasses vs hand-written Zod).
Shipped 2026-09-19: strict Pydantic response models on /overview, /anomalies, /optimise/latest
(`app/response_models.py`, `extra="forbid"` — undeclared backend fields now fail tests loudly);
committed `src/backend/openapi.json`; `npm run gen:api` → `src/lib/api-types.gen.ts`; CI fast job
re-exports the schema, regenerates, and fails on diff. Also 2026-09-19: hand-written `schemas.ts`
**deleted** (its Quality schema already expected `code` where the backend sends `terminal_code` —
the drift it existed to prevent); `api.ts` overview call no longer warns-and-ignores a safeParse.
Runtime contract is enforced server-side by the strict response models; generated types are the
frontend's single reference.
Also 2026-09-19: `lib/contract.ts` pins the /api/overview runtime schema to the generated type
in **both directions** (build breaks on drift either way) and `api.overview()` **throws**
`ApiValidationError` on a violating payload — no warn-and-render. Plan GET is covered by the
strict `PlanResponse` model, and the UI surfaces plan provenance ("generated from forecast run X
+ optimiser run Y").
**Closed 2026-09-20 (remaining scope):** strict response models now cover **every** read route
(forecast, terminals, vessels, hotspots, routing, plan, quality, weather, anomalies, bob history,
scenarios, optimise) — `extra="forbid"` caught two real shape drifts on attach (forecast
`horizons` is a dict, POST /optimise carries `horizon_hours`/`params`). Frontend: every `api.*`
call now parses through a `contract.ts` schema pinned to the generated type — a violating
payload throws `ApiValidationError` on all endpoints, not just /api/overview.
Also 2026-09-20 (brutal-audit follow-up): Bob's primary agent path is no longer prompt-only —
`agent_grounding_verdict()` rejects answers with zero MCP tool calls or no recognised engine
tool (server-prefixed names matched) and falls back to the deterministic engine pack, surfacing
`grounded` + `verification` in the response and chat history; `bob_agent.run` retries only
transient timeouts, failing fast on deterministic failures.

### B-8 CI has no frontend tests 🟢 — CLOSED 2026-09-20
Raised by: audit — playtests found more UI defects (delta color inversion, blank yard, UNAVAILABLE
pill, KPI flash) than API defects.
Closed: `src/frontend/e2e/smoke.spec.ts` — 3 Playwright tests (Overview KPI values, BerthCranes
CP-SAT wait-delta headline, unknown deep link → Overview) against contract-shaped API mocks,
wired into the `fast` CI job. 3/3 green locally; writing them immediately caught a component
crash on the `terminals` shape (fixed by fixture).

### B-9 Environment bootstrap is tribal knowledge 🟢 — CLOSED 2026-09-20
Raised by: session restarts repeatedly killed servers; Windows-bound `.venv/Scripts` paths.
Closed: `scripts/dev.sh` (seed-if-empty, idempotent port checks, health wait, `--reset` flag)
verified on the running stack; `npm run dev:all` alias added; documented in `docs/development.md`.

## Closed

- ~~`GET /api/tides` writes on read (§11 audit finding)~~ — fixed 2026-09-20: the GET is now
  purely read-only (serves persisted rows / labelled harmonic model; `noaa_rows_written` key
  removed); the NOAA fetch + window ensure live at startup and `POST /api/tides/refresh` only.
  Same fix exposed that the NOAA write path could never persist (its inserts collided with
  persisted harmonic rows on `uq_tide_berth_hours`) — the fetch now replaces the rows its
  horizon covers. Proven live: two GETs byte-identical with stable row count; startup log
  `NOAA CO-OPS (637 rows)`; refresh `rows_written: 1261, source noaa-coops`. Pinned by
  `test_tides_get_is_idempotent`, `test_tides_refresh_is_the_write_path`, and
  `test_noaa_fetch_replaces_harmonic_rows_in_its_horizon`.

- ~~Weather chain structurally dead (sign bug + row gate)~~ — fixed 2026-09-19 in
  `app/pipelines/weather.py` (sign convention) + `MIN_WEATHER_ROWS=2`; startup now loads 58 rows;
  `weather_used` reachable and honestly false on calm seas. Proven by live startup log + forecast API.
- ~~Zone cards render blank `yard [%]`~~ — fixed: backend emits `yard_util_pct`; simulator gate
  made two-way with target reversion (yards hold 56–65%); forecast consumes live inventory via
  `live_yard`. Proven by `/api/overview` + Forecast tab yard chart.
- ~~Status pill shows UNAVAILABLE while healthy; double-polls /api/overview~~ — fixed in
  `SystemStatus.tsx` (shared React Query cache, honest CONNECTING state).
- ~~Berth & Cranes KPI delta colored inverted~~ — fixed in `BerthCranes.tsx` (sign convention now
  matches the compare table).
- ~~`narrative_source: null` on GET /api/plan~~ — fixed in `routers/plan.py`.
- ~~Congestion page KPI flash 0/UNKNOWN on load~~ — fixed in `pages/CongestionPage.tsx`.
- ~~Dead-local assignments (F841) chased in five separate commits~~ — rule re-enabled in
  `pyproject.toml` (0 violations); exceptions now require `# noqa: F841` + reason.
- ~~Full 3-minute test suite on every push~~ — split CI: `fast` job (lint + `-m "not slow"` ≈3s
  backend + typecheck) on every push; `full` job (suite + build + submission validation) on PRs to main.
  Proven: fast suite = 10 passed in 1.61s locally.
- ~~B-1 Anomaly detector fires on 3 of 4 zones every run~~ — closed 2026-09-19 via the acceptance's
  documented threshold path: `contamination='auto'` + evidence floor `SCORE_FLOOR=0.2`; a flag now
  requires novelty AND (forest score ≤ −0.2 OR magnitude |z| ≥ 3.5), and detail text says when a
  weak signal is held below the floor. Seeded PCT outage strengthened to a 96h crane-pool collapse —
  the old 0.5× rate was invisible per-zone (any in-window service outlasts the sim horizon) and B9
  passed only through the old noise. Fresh seed: 3/4 flagged, all |score| ≥ 0.2 (LBCT drift −0.08
  correctly silent); full suite green.
- ~~B-2 CP-SAT solve stops far from optimal~~ — closed 2026-09-19 via the acceptance's documentation
  path: `relative_gap_limit=0.10` (near-proven runs now finish OPTIMAL) + `num_workers=0` (all cores,
  per sat_parameters.proto) + a gap chip in the Berth & Cranes solver line marking time-limited runs.
  Live: FEASIBLE, gap 16.1% (was 52.4%) at the same 8s budget — documented, not implied optimal.
- ~~B-5 GET /api/quality performs writes on every read~~ — closed 2026-09-19: GET is read-only;
  normalisation + completeness recompute moved to an explicit pass run at startup (`main.py`
  lifespan, "data-quality pass" log line) and `POST /api/quality/refresh`. Proven by
  `test_quality_get_is_idempotent` (identical bodies, no new rows) and a live double-GET diff.
- ~~Plan provenance dropped at the read boundary (spec §6)~~ — closed 2026-09-19: GET /api/plan
  now serves `plan_id`/`created_at`/`forecast_run_id`/`optimiser_run_id` from the persisted row
  (fresh builds surface the run ids from summary). Pinned by `test_plan_get_serves_provenance`.
- ~~Frontend validation decorative (safeParse → warn → raw)~~ — closed 2026-09-19 by removing the
  false-safety layer with `schemas.ts`: the contract is enforced server-side (strict response
  models) and CI-pinned via generated types.
