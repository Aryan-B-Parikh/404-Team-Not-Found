# Research notes — CP-SAT gap, LightGBM bands, anomaly tuning, API client generation

> **Superseded 2026-09-20 (API-client section only):** the hand-written `schemas.ts`
> discussed below has since been **deleted** (see backlog B-7). The contract is now:
> strict backend response models → committed `openapi.json` → generated
> `api-types.gen.ts` → `lib/contract.ts` runtime pin. The primary-source research
> content below is unchanged.

Date: 2026-09-19 · Method: investigated against primary sources (official docs, the
OR-Tools parameter proto, scikit-learn/LightGBM references, tool READMEs); every claim
links to the source that owns it. Repo observations cite this repo's files.
Related backlog items: B-1 (anomaly noise), B-7 (contract drift), optimiser gap
(audit finding), forecast bands (W2/W3).

---

## 1. OpenAPI → TypeScript client generation (unblocks B-7)

**Current state (repo).** `frontend/src/lib/schemas.ts` is a hand-written Zod mirror of
backend payloads. It drifted twice (`yard_util_pct`, hotspot `confidence`); the
tripwire test added this week catches three pinned fields, but the schemas themselves
are still maintained by hand. FastAPI already serves the machine-readable contract at
`/openapi.json` (framework default).

**Findings.**

- **`openapi-zod-client` is out.** Its own README states it is "not maintained
  anymore" and points users elsewhere — [repo README](https://github.com/astahmer/openapi-zod-client).
- **orval** generates Zod schemas directly from an OpenAPI spec via `client: 'zod'`,
  emits Zod 3 *or* 4 (pinnable via `override.zod.version` for deterministic CI
  output), supports per-operation/per-tag overrides (`coerce`, `strict`), and can
  also emit TanStack Query hooks — which matches this repo's React Query usage.
  — [orval Zod guide](https://orval.dev/docs/guides/zod)
- **@hey-api/openapi-ts** is the other actively-maintained generator: TypeScript SDK
  plus a Zod-schemas plugin and a TanStack Query plugin among "20+ plugins"; used in
  production at Vercel/PayPal/AWS per its README.
  — [hey-api/openapi-ts README](https://github.com/hey-api/openapi-ts)
- **openapi-typescript** is the lighter, types-only option (no runtime Zod); surveys
  position it as the minimal footprint with room to add Zod/Query plugins later —
  [third-party survey, secondary source](https://dev.to/nyaomaru/which-openapi-codegen-should-you-choose-openapi-typescript-vs-hey-api-vs-orval-vs-kubb-100p).

**Recommendation.** orval in `client: 'zod'` mode: one config file, a `gen:api` script
that fetches `/openapi.json`, generated `schemas.gen.ts` committed, and a CI step that
regenerates and fails on diff. Keep the hand-written `schemas.ts` only for
frontend-internal shapes.

**Prerequisite, important.** Most backend routers return hand-built dicts (e.g.
`pipeline.build_overview`), so FastAPI's OpenAPI output for those endpoints is
generic/empty. Step 0 of B-7 is declaring Pydantic `response_model`s on the routers —
that work is what actually creates the single-owned contract; the generator is just
the consumer. Cost: ~1–2 days total (models 1 day, wiring 0.5).

---

## 2. CP-SAT optimality gap (52% at timeout)

**Current state (repo).** `optimiser.py:255-259`: `num_search_workers = 8`,
`max_time_in_seconds = 8.0` (3.0 incremental). Live runs report `gap_pct ≈ 52%`.

**Findings.**

- `relative_gap_limit` / `absolute_gap_limit` stop the solver once the objective is
  provably within the bound by that margin (e.g. `0.05` = "within 5% of optimum,
  proven"); status stays OPTIMAL when reached.
  — [CP-SAT Primer, Parameters](https://d-krupke.github.io/cpsat-primer/parameters.html)
- `num_workers = 0` means "use all cores" (8 is a hard-coded guess in this repo).
  — [sat_parameters.proto, official](https://github.com/or-tools/or-tools/blob/stable/ortools/sat/sat_parameters.proto)
- The primer's central advice: **few parameters help; model quality dominates.**
  Enable `log_search_progress` during development to see whether the *bound* or the
  *solution* is the slow side, and whether presolve removes most of the model.
- A solver timeout with a large gap means the reported objective is *feasible, not
  proven*; `solver.best_objective_bound` carries the quality certificate.
  — [official CP-SAT solver docs](https://developers.google.com/optimization/cp/cp_solver)

**Recommendation (honest first, clever later).**
1. Ship `best_objective_bound` + `gap_pct` in the optimise API response — the UI can
   then say "within X% of proven optimum" instead of implying optimality.
2. One dev run with `log_search_progress = True`; if presolve shows a huge model or a
   bound that never moves, the fix is model structure (tighten crane-interval
   formulation, widen `SCALE` granularity), not parameters.
3. Set `num_workers = 0` unless 8 is deliberate; consider `relative_gap_limit = 0.10`
   so near-proven runs *return* as proven instead of burning the rest of the budget.
Cost: instrumentation + measurement ~0.5 day; model work only if (2) justifies it.

---

## 3. LightGBM forecast uncertainty bands

**Current state (repo).** `forecasting.py` already trains quantile models at
α 0.1 / 0.9 (docstring: bands "almost for free") plus a `Z_80 = 1.2816` normal
fallback and band-width-driven confidence. `weather_adjust.py` widens bands under
adverse weather.

**Findings.**

- `objective: quantile` is a first-class LightGBM objective (aliases:
  quantile regression); `alpha` selects the quantile for quantile/huber objectives —
  one model per quantile is the documented usage pattern.
  — [LightGBM Parameters](https://lightgbm.readthedocs.io/en/latest/Parameters.html)
- The two-model (α=0.05 / α=0.95) pattern for prediction intervals is the standard
  recipe — [IBM developer tutorial, secondary](https://developer.ibm.com/articles/prediction-intervals-explained-a-lightgbm-tutorial/).
- Known failure mode of per-quantile models: **quantile crossing** (P10 > P90 at some
  horizon). The standard guard is a monotonic post-pass (swap/sort the pair). This
  repo's band construction should be checked for it — one assertion in
  `test_contracts.py` would pin it.
- Deeper alternative not verified in this pass: **conformal prediction** (e.g. the
  MAPIE library) gives distribution-free coverage guarantees on top of any point
  model — flagged as *further reading*, not a recommendation yet.

**Recommendation.** Keep the quantile setup; add (a) a quantile-crossing assertion,
(b) an empirical **coverage check** — the repo already computes validation buckets,
so extend one to report "% of holdout points inside the 80% band"; if coverage is
far from 80%, recalibrate α or the band-width confidence mapping. Cost: ~0.5 day.

---

## 4. Anomaly detector noise (backlog B-1)

**Current state (repo).** `anomaly.py`: IsolationForest per zone,
`CONTAMINATION = 0.04`, `MIN_SAMPLES = 96`, plus a hand-rolled `STAT_Z = 3.5`
and DATA_ERROR classification. Live behavior: 3 of 4 zones flagged every run.

**Findings.**

- `contamination` (float) **defines the decision threshold so the training data
  contains exactly that proportion of outliers**: "the offset is defined in such a
  way we obtain the expected number of outliers … in training." With 0.04 on a
  72–336 h window, several points per zone are guaranteed to be labelled — the
  observed noise is the *configured* outcome, not model misbehavior.
  — [scikit-learn IsolationForest docs](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- `contamination='auto'` (the sklearn ≥0.22 default) instead uses the original
  paper's offset (−0.5), flagging only genuinely short-isolation-path samples.
- Same-API alternatives if IsolationForest stays weak: `LocalOutlierFactor`,
  `OneClassSVM` (cross-referenced in the same docs page).

**Recommendation.** Try `contamination='auto'` first (one line + reseed +
live check of the alert list); combine with the existing `STAT_Z` gate so a flag
requires both forest novelty and a magnitude threshold. Only if that under-detects,
look at residual-based detection against the forecast band as the deeper redesign.
Cost: ~0.5 day.

---

## Suggested order (value ÷ cost)

1. **Anomaly `contamination='auto'`** — one line, closes B-1's worst symptom.
2. **Band coverage + crossing checks** — makes the headline confidence number defensible.
3. **CP-SAT bound instrumentation** — turns "52% gap" into an honest quality statement.
4. **orval adoption (B-7)** — largest change; prerequisite response-models work is also
   the real contract fix.
