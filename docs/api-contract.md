# API Contract (frozen — Phase 0)

> **Do not change a path or a response key without the Integrator.** `tests/test_contracts.py` asserts these
> paths and shapes; the frontend is typed against them via the **generated** contract
> (`src/backend/openapi.json` → `npm run gen:api` → `src/frontend/src/lib/api-types.gen.ts`), with
> `src/frontend/src/lib/contract.ts` pinning the /api/overview runtime schema to that type.
> Owners implement the logic behind the frozen stub; they do **not** rename keys.

Base URL: `http://localhost:8000`. All JSON unless noted. `stub: true` marks a Phase-0 placeholder.

## Existing (already implemented)

| Method | Path | Owner | Key response fields |
|---|---|---|---|
| GET | `/health` | Integrator | `{status}` |
| GET | `/api/overview` | Integrator | `{t0, dataset, kpis, zones[], alerts[], hotspots, anomalies[], arrivals_timeline[]}` |
| GET | `/api/forecast?zone=` | W2 | `{t0, dataset_source, summary{}, selected{}, hotspots, anomalies, weather_used, confidence}` |
| GET | `/api/optimise/latest` | W3 | `{run_id, solver, status, objective, solve_ms, assignments[], metrics, baseline, deltas, deferred[], weights, tidal_feasible, incremental}` |
| POST | `/api/optimise` | W3 | as `/latest` + `tidal_feasible`, `incremental`, `gap_pct`. Request body: `{crane_factor, move_rate_per_crane_hour, incremental?, tidal?}` |
| GET | `/api/routing` | W3 | `{recommendations[{…, option_detail:{rule, berthing_window, alternate_terminal}}], counts{}, total_savings_usd, cost_model}` |
| GET | `/api/plan?text=1` | W3 | `{summary{…, confidence_by_bucket{}}, shifts[], text, narrative_source, plan_id, created_at, forecast_run_id, optimiser_run_id}` — provenance ids null on fresh builds, set on persisted plans |
| POST | `/api/plan` | W3 | as GET with the lineage ids always set (persisted plan) |
| GET | `/api/terminals` | W1 | `{terminals[{code,name,pier,berth_length_ft,deepsea_berths,gantry_cranes,capacity_teu_m,zone_code,note,berths[],cranes[],yard_zones[],gate}], source}` |
| GET | `/api/vessels` | W1 | `{vessels[{…, assignment, deferred}]}` |
| GET | `/api/hotspots` | Integrator | `{ranked[], most_actionable, method}` |
| GET | `/api/export?type=` | Integrator | CSV (`assignments\|routing\|vessels\|forecast`) |
| GET/POST | `/api/bob` | Integrator | GET `{messages[]}` · POST `{content, actions[], mode, provider, intent}` (`provider` = `bob\|deterministic`) |

## New (frozen in Phase 0 — implement behind the flag)

| Method | Path | Owner | Flag | Frozen response shape |
|---|---|---|---|---|
| GET | `/api/quality` | W1 | `FEATURE_QUALITY` | `{terminals:[{terminal_code, name, completeness_pct, missing:[], rules_version}], rules_version, last_run_at}` — **read-only**; normalisation writes live at startup and `POST /api/quality/refresh` |
| POST | `/api/quality/refresh` | W1 | — | `{status, normalised_rows_updated}` — the explicit normalisation write path |
| GET | `/api/tides?hours=72` | W3 | — | `{period_hours, amplitude_ft, under_keel_margin_ft, source, berths:[{berth_id, berth_name, design_depth_ft, curve:[{hour, depth_ft}]}]}` — **read-only**; serves persisted rows (`source` = `noaa-coops` when NOAA rows exist, else `harmonic-model`) |
| POST | `/api/tides/refresh` | W3 | — | `{source, rows_written, station, hours}` — the explicit NOAA fetch / window-ensure write path |
| GET | `/api/weather?hours=72` | W1 | `FEATURE_WEATHER` | `{points:[{hour, ts, wind_kn, wave_m}], source, hours}` |
| POST | `/api/vessels/upload` | W1 | `FEATURE_UPLOAD` | `{accepted, rejected, errors:[], revisions_created, upload_id, filename}` |
| GET | `/api/anomalies` | W2 | — | `{anomalies:[{zone_code, kind, method, score, is_anomaly, sample_size, detail, features}]}` |
| POST | `/api/scenarios` | W3 | — | `{scenario_id, params, baseline, scenario, impact, weights, solver}` |
| POST | `/api/scenarios/extended` | W3 | `FEATURE_SCENARIOS_EXT` | `{baseline, scenario, impact{…}, feasible, kind, parent_scenario_id, scenario_id, description, solver}` · request: `{kind, crane_factor, move_rate_per_crane_hour, terminal_code?, berth_count_delta?, bunching_vessels?, schedule_shift_hours?, parent_scenario_id?}` · 400 on contradictory params |
| POST | `/api/scenarios/{id}/rollback` | W3 | `FEATURE_SCENARIOS_EXT` | `{restored, scenario_id, status}` (404 if unknown) |

## Shared DB fields added in Phase 0 (see `app/models.py`)

| Table | New |
|---|---|
| `vessel_call` | `voyage_number`, `normalised` (JSONB) |
| `forecast_run` | `data_version`, `feature_flags` (JSONB) |
| `routing_recommendation` | `option_detail` (JSONB) |
| `operations_plan` | `confidence_json` (JSONB) |
| `scenario` | `parent_scenario_id`, `status` |
| **new tables** | `weather_observation`, `terminal_quality`, `tidal_window`, `vessel_schedule_upload` |

## Rules for owners

1. Implement behind your flag; **do not** rename paths or keys.
2. If you need a new key, add it **additively** (never remove/rename) and update this file + `types.ts` in the same PR.
3. Any change to a shared file (`models.py`, `main.py`, `reference.py`, `serialize.py`, `pipeline.py`, `mcp_server.py`) → PR to the Integrator.
4. Run `uv run pytest tests/ -q` before pushing; a contract test failure means a downstream break.
