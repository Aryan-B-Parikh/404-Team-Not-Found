// Runtime contract validation for every dashboard-read endpoint.
//
// Compile-pinned in BOTH directions (overview) and forward (the rest): if a schema and
// the generated `components["schemas"]` ever diverge, the pin assignments fail the
// build — this mirror cannot drift the way the old hand-written schemas.ts did
// (deleted 2026-09-19). Brutal-audit finding: /api/overview was the only validated
// call; every other api.ts call now parses through a pinned schema too.
//
// Enforcement (Option A): api.* throws ApiValidationError on a violating payload —
// malformed data is never rendered; callers land in their existing React Query error
// states. Dynamic dict fields validate as records (z.any) so component code keeps its
// existing loose indexing; the top-level shape and primitives are strict.
import { z } from "zod";
import type { components } from "./api-types.gen";

const _num = z.number();
const _rec = z.record(z.string(), z.unknown());
const _recAny = z.record(z.string(), z.any());
const _bool = z.boolean();
const _str = z.string();

const KpisSchema = z.object({
  vessels_at_anchor: _num, vessels_inbound: _num, avg_anchorage_wait: _num,
  max_anchored_hours: _num, arrivals_next24: _num, port_index_now: _num,
  peak_forecast_index: _num, peak_forecast_hour: _num, moves_pending: _num,
  daily_fleet_burn_usd: _num, berth_util_pct: _num, crane_util_pct: _num,
});

const ZoneSchema = z.object({
  zone_code: z.string(), label: z.string(), level: z.string(), trend: z.string(),
  current_index: _num, peak_index: _num, peak_hour: _num, recent_index: z.array(_num),
  queue_now: _num, wait_now: _num, yard_util_pct: _num, berths: _num, cranes: _num,
});

const AlertSchema = z.object({
  severity: z.string(), title: z.string(), detail: z.string(), hour: _num.nullable().optional(),
});

const HotspotSchema = z.object({
  zone_code: z.string(), zone_name: z.string(), risk_score: _num, confidence: _num,
  peak_index: _num, peak_hour: _num, binding_constraint: z.string(),
  binding_evidence: _rec, resource_pressure: _rec, explanation: z.string(),
  components: _rec, weights: _rec,
});

const HotspotsShape = z.object({
  ranked: z.array(HotspotSchema),
  most_actionable: HotspotSchema.optional(),
  method: z.string().optional(),
});

export const OverviewSchema = z.object({
  t0: z.string(),
  dataset: z.object({ source: z.string(), note: z.string() }),
  data_version: z.string(),
  weather_used: z.boolean(),
  confidence: _num,
  kpis: KpisSchema,
  zones: z.array(ZoneSchema),
  alerts: z.array(AlertSchema),
  hotspots: HotspotsShape,
  anomalies: z.array(_rec),
  arrivals_timeline: z.array(z.object({ hour: _num, count: _num })),
  last_updated: z.string(),
});

// Two-way structural pin: build breaks if the schema under- or over-covers the
// generated contract type. (z.output, not satisfies — Zod 4's ZodType generics
// reject object literals on variance, and these assignments catch drift both ways.)
type _OverviewOut = z.output<typeof OverviewSchema>;
const _pinForward: components["schemas"]["Overview"] = null as unknown as _OverviewOut;
const _pinReverse: _OverviewOut = null as unknown as components["schemas"]["Overview"];
void _pinForward; void _pinReverse;

// ---------------------------------------------------------------- all other reads
// Forward pins: each schema's output must be assignable to the generated type — this
// forces coverage of every REQUIRED field and forbids demanding types the backend
// never declared, while allowing omission of truly optional fields.

export const ForecastSchema = z.object({
  t0: _str, dataset_source: _str, summary: _recAny, selected: _recAny,
  hotspots: HotspotsShape, anomalies: z.array(_recAny),
  weather_used: _bool, confidence: _num,
  confidence_by_horizon: _recAny, horizons: _recAny, provenance: _recAny,
});

export const TerminalsSchema = z.object({ terminals: z.array(_recAny), source: _str });
export const VesselsSchema = z.object({ vessels: z.array(_recAny) });
export const HotspotsResponseSchema = HotspotsShape;

export const RoutingSchema = z.object({
  recommendations: z.array(_recAny), counts: z.record(_str, _num),
  total_savings_usd: _num, cost_model: _recAny,
});

export const PlanSchema = z.object({
  summary: _recAny, shifts: z.array(_recAny), text: _str, narrative_source: _str,
  plan_id: _num.nullable().optional(), created_at: _str.nullable().optional(),
  forecast_run_id: _num.nullable().optional(), optimiser_run_id: _num.nullable().optional(),
});

export const QualitySchema = z.object({
  terminals: z.array(_recAny), rules_version: _str,
  last_run_at: _str.nullable().optional(), stub: _bool.optional(),
});

export const WeatherSchema = z.object({
  points: z.array(_recAny), source: _str, hours: _num, stub: _bool.optional(),
});

export const AnomaliesSchema = z.object({
  anomalies: z.array(_recAny), method: _str, generated_at: _str, weather_used: _bool,
});

export const BobHistorySchema = z.object({ messages: z.array(_recAny) });

export const BobAnswerSchema = z.object({
  content: _str, actions: z.array(z.string()), mode: _str, provider: _str,
  intent: _str, grounded: _bool.optional(),
});

export const OptimiseSchema = z.object({
  run_id: _num.nullable().optional(), solver: _str, status: _str,
  objective: _num.nullable().optional(), solve_ms: _num,
  assignments: z.array(_recAny), metrics: _recAny, baseline: _recAny, deltas: _recAny,
  deferred: z.array(_recAny), weights: _recAny,
  tidal_feasible: _bool.optional(), incremental: _bool.optional(),
  gap_pct: _num.nullable().optional(),
  horizon_hours: _num.nullable().optional(), params: _recAny.nullable().optional(),
});

export const ScenarioSchema = z.object({
  scenario_id: _num, params: _recAny, baseline: _recAny, scenario: _recAny,
  impact: _recAny, weights: _recAny, solver: _recAny,
});

export const ScenarioExtendedSchema = z.object({
  baseline: _recAny, scenario: _recAny, impact: _recAny, feasible: _bool, kind: _str,
  parent_scenario_id: _num.nullable().optional(), scenario_id: _num, description: _str,
  forecast: _recAny, solver: _recAny, weights: _recAny,
});

export const ScenarioRollbackSchema = z.object({ restored: _bool, scenario_id: _num, status: _str });

// ---- previously raw-fetch()ed in components (brutal-review sweep) ----
export const AisStatusSchema = z.object({
  source: _str, rows: _num, zones: _num, track_points: _num,
  newest_ts: _str.nullable().optional(), oldest_ts: _str.nullable().optional(), stub: _bool.optional(),
});

export const AisGenerateSchema = z.object({
  status: _str, source: _str, message: _str,
  rows_scanned: _num, skipped: _num, vessels: _num, hours: _num, output_rows: _num,
  inserted: _num, is_measured: _bool, zones: _num, newest_ts: _str, days: _num, seed: _num,
  stub: _bool.optional(),
});

export const TidesSchema = z.object({
  period_hours: _num, amplitude_ft: _num, under_keel_margin_ft: _num,
  source: _str, berths: z.array(_recAny),
});

export const UploadSchema = z.object({
  accepted: _num, rejected: _num, errors: z.array(_str), revisions_created: _num,
  normalised_rows: _num.nullable().optional(), upload_id: _num.nullable().optional(),
  filename: _str.nullable().optional(), bytes: _num.nullable().optional(),
  stub: _bool.optional(), replan: _recAny.nullable().optional(),
});

export const BobStatusSchema = z.object({
  provider: _str, configured: _bool, cli_available: _bool, mcp: _str, tools: _num, fallback: _str,
});

export const HealthSchema = z.object({ status: _str });

// Forward pins: build breaks if a schema stops covering its generated contract type.
type _Out<T extends z.ZodType> = z.output<T>;
const _fwd = <T extends z.ZodType, G>(out: _Out<T>) => null as unknown as G;
void _fwd;

const _pinForecast = _fwd<typeof ForecastSchema, components["schemas"]["ForecastResponse"]>(null!);
const _pinTerminals = _fwd<typeof TerminalsSchema, components["schemas"]["TerminalsResponse"]>(null!);
const _pinVessels = _fwd<typeof VesselsSchema, components["schemas"]["VesselsResponse"]>(null!);
const _pinRouting = _fwd<typeof RoutingSchema, components["schemas"]["RoutingResponse"]>(null!);
const _pinPlan = _fwd<typeof PlanSchema, components["schemas"]["PlanResponse"]>(null!);
const _pinQuality = _fwd<typeof QualitySchema, components["schemas"]["QualityResponse"]>(null!);
const _pinWeather = _fwd<typeof WeatherSchema, components["schemas"]["WeatherResponse"]>(null!);
const _pinAnomalies = _fwd<typeof AnomaliesSchema, components["schemas"]["AnomaliesResponse"]>(null!);
const _pinBobHistory = _fwd<typeof BobHistorySchema, components["schemas"]["BobHistoryResponse"]>(null!);
const _pinBobAnswer = _fwd<typeof BobAnswerSchema, components["schemas"]["BobAnswerResponse"]>(null!);
const _pinOptimise = _fwd<typeof OptimiseSchema, components["schemas"]["OptimiseLatest"]>(null!);
const _pinScenario = _fwd<typeof ScenarioSchema, components["schemas"]["ScenarioResponse"]>(null!);
const _pinScenarioExt = _fwd<typeof ScenarioExtendedSchema, components["schemas"]["ScenarioExtendedResponse"]>(null!);
const _pinRollback = _fwd<typeof ScenarioRollbackSchema, components["schemas"]["ScenarioRollbackResponse"]>(null!);
const _pinAisStatus = _fwd<typeof AisStatusSchema, components["schemas"]["AisStatusResponse"]>(null!);
const _pinAisGenerate = _fwd<typeof AisGenerateSchema, components["schemas"]["AisGenerateResponse"]>(null!);
const _pinTides = _fwd<typeof TidesSchema, components["schemas"]["TidesResponse"]>(null!);
const _pinUpload = _fwd<typeof UploadSchema, components["schemas"]["UploadResponse"]>(null!);
const _pinBobStatus = _fwd<typeof BobStatusSchema, components["schemas"]["BobStatusResponse"]>(null!);
const _pinHealth = _fwd<typeof HealthSchema, components["schemas"]["HealthResponse"]>(null!);
void _pinForecast; void _pinTerminals; void _pinVessels; void _pinRouting; void _pinPlan;
void _pinQuality; void _pinWeather; void _pinAnomalies; void _pinBobHistory; void _pinBobAnswer;
void _pinOptimise; void _pinScenario; void _pinScenarioExt; void _pinRollback;
void _pinAisStatus; void _pinAisGenerate; void _pinTides; void _pinUpload; void _pinBobStatus; void _pinHealth;

export class ApiValidationError extends Error {
  constructor(public endpoint: string, public issues: z.ZodError["issues"]) {
    super(`API contract violation at ${endpoint}: ${issues.length} issue(s)`);
    this.name = "ApiValidationError";
  }
}
