// Centralized API client for the FastAPI gateway.
// Runtime contract: enforced server-side by strict Pydantic response models
// (extra="forbid"), CI-pinned via api-types.gen.ts, and validated client-side
// here — EVERY call parses its response through a contract.ts schema pinned to
// the generated type. A violating payload throws ApiValidationError, so malformed
// data is never rendered; callers land in their existing error states
// (brutal-audit finding: previously only /api/overview was validated).
import type { ScenarioExtendedRequest } from "../types";
import {
  AisGenerateSchema, AisStatusSchema, AnomaliesSchema, ApiValidationError, BobAnswerSchema,
  BobHistorySchema, BobStatusSchema, ForecastSchema, HealthSchema, HotspotsResponseSchema,
  OptimiseSchema, OverviewSchema, PlanSchema, QualitySchema, RoutingSchema,
  ScenarioExtendedSchema, ScenarioRollbackSchema, ScenarioSchema, TerminalsSchema, TidesSchema,
  UploadSchema, VesselsSchema, WeatherSchema,
} from "./contract";
import type { z } from "zod";

export class ApiError extends Error {
  constructor(message: string, public status: number, public endpoint: string) { super(message); this.name = "ApiError"; }
}

/** Parse a raw payload against a pinned contract schema (Option A: throw, never render). */
function parse<S extends z.ZodType>(endpoint: string, schema: S, raw: unknown): z.output<S> {
  const r = schema.safeParse(raw);
  if (!r.success) throw new ApiValidationError(endpoint, r.error.issues);
  return r.data;
}

export async function get<T = any>(path: string): Promise<T> {
  try { const r = await fetch(path); if (!r.ok) throw new ApiError(`Request failed with status ${r.status}`, r.status, path); return await r.json(); }
  catch (err: any) { if (err instanceof ApiError) throw err; throw new ApiError(err?.message || `Unable to reach ${path}`, 0, path); }
}
export async function post<T = any>(path: string, body?: unknown): Promise<T> {
  try { const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) }); if (!r.ok) throw new ApiError(`POST ${path} failed with status ${r.status}`, r.status, path); return await r.json(); }
  catch (err: any) { if (err instanceof ApiError) throw err; throw new ApiError(err?.message || `Unable to execute POST ${path}`, 0, path); }
}
export async function upload<T = any>(path: string, file: File): Promise<T> {
  try { const fd = new FormData(); fd.append("file", file); const r = await fetch(path, { method: "POST", body: fd }); if (!r.ok) throw new ApiError(`Upload to ${path} failed with status ${r.status}`, r.status, path); return await r.json(); }
  catch (err: any) { if (err instanceof ApiError) throw err; throw new ApiError(err?.message || `Failed to upload file to ${path}`, 0, path); }
}

/** Validated GET: fetch + parse against a pinned schema. */
async function getValidated<S extends z.ZodType>(path: string, schema: S): Promise<z.output<S>> {
  return parse(path, schema, await get(path));
}

export const api = {
  overview: async () => getValidated("/api/overview", OverviewSchema),
  forecast: (zone: string) => getValidated(`/api/forecast?zone=${encodeURIComponent(zone)}`, ForecastSchema),
  terminals: () => getValidated("/api/terminals", TerminalsSchema),
  vessels: () => getValidated("/api/vessels", VesselsSchema),
  hotspots: () => getValidated("/api/hotspots", HotspotsResponseSchema),
  routing: () => getValidated("/api/routing", RoutingSchema),
  plan: () => getValidated("/api/plan", PlanSchema),
  optimiseLatest: () => getValidated("/api/optimise/latest", OptimiseSchema),
  optimise: async (body: { crane_factor: number; move_rate_per_crane_hour: number; incremental?: boolean; tidal?: boolean }) =>
    parse("/api/optimise", OptimiseSchema, await post("/api/optimise", body)),
  bobHistory: () => getValidated("/api/bob", BobHistorySchema),
  bobStatus: () => getValidated("/api/bob/status", BobStatusSchema),
  bob: async (message: string) => parse("/api/bob", BobAnswerSchema, await post("/api/bob", { message })),
  exportUrl: (type: string) => `/api/export?type=${type}`,
  health: () => getValidated("/health", HealthSchema),
  anomalies: () => getValidated("/api/anomalies", AnomaliesSchema),
  quality: () => getValidated("/api/quality", QualitySchema),
  weather: (hours = 72) => getValidated(`/api/weather?hours=${hours}`, WeatherSchema),
  aisStatus: () => getValidated("/api/ais/status", AisStatusSchema),
  aisGenerate: async (days: number, seed: number) =>
    parse(`/api/ais/generate?days=${days}&seed=${seed}`, AisGenerateSchema,
          await post(`/api/ais/generate?days=${days}&seed=${seed}`)),
  tides: () => getValidated("/api/tides", TidesSchema),
  weatherRefresh: async () => parse("/api/weather/refresh", WeatherSchema, await post("/api/weather/refresh")),
  uploadSchedule: async (file: File) => parse("/api/vessels/upload", UploadSchema, await upload("/api/vessels/upload", file)),
  scenario: async (body: { crane_factor: number; move_rate_per_crane_hour: number }) =>
    parse("/api/scenarios", ScenarioSchema, await post("/api/scenarios", body)),
  scenarioExtended: async (body: ScenarioExtendedRequest) =>
    parse("/api/scenarios/extended", ScenarioExtendedSchema, await post("/api/scenarios/extended", body)),
  scenarioRollback: async (id: number) =>
    parse(`/api/scenarios/${id}/rollback`, ScenarioRollbackSchema, await post(`/api/scenarios/${id}/rollback`)),
};
export const fmtUsd = (n: number) => `$${Math.round(n).toLocaleString()}`;
export const fmtNum = (n: number) => Math.round(n).toLocaleString();
