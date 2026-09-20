// Shared TS types mirroring docs/api-contract.md. Add types here rather than in tabs.
export interface QualityRow {
  code: string;
  name: string;
  completeness_pct: number | null;
  missing: string[];
}
export interface QualityResponse {
  terminals: QualityRow[];
  rules_version: string;
  stub?: boolean;
}
export interface WeatherPoint {
  hour: number;
  ts: string;
  wind_kn: number | null;
  gust_kn: number | null;
  wave_m: number | null;
  visibility_km: number | null;
}
export interface WeatherResponse {
  points: WeatherPoint[];
  source: string;
  hours: number;
  stub?: boolean;
}
export interface UploadResponse {
  accepted: number;
  rejected: number;
  errors: string[];
  revisions_created: number;
  upload_id: number | null;
  filename: string;
  stub?: boolean;
}
export interface ScenarioExtendedRequest {
  kind: string;
  crane_factor: number;
  move_rate_per_crane_hour: number;
  terminal_code?: string;
  berth_count_delta?: number;
  bunching_vessels?: number;
  parent_scenario_id?: number;
}
export interface ScenarioExtendedResponse {
  baseline: Record<string, unknown>;
  scenario: Record<string, unknown>;
  impact: Record<string, unknown>;
  feasible: boolean;
  kind: string;
  parent_scenario_id: number | null;
  stub?: boolean;
}

// --- W3 tidal windows (GET /api/tides) ---
export interface TidePoint {
  hour: number;
  depth_ft: number;
}
export interface TideBerth {
  berth_id: number;
  berth_name: string;
  design_depth_ft: number;
  curve: TidePoint[];
}
export interface TidesResponse {
  period_hours: number;
  amplitude_ft: number;
  under_keel_margin_ft: number;
  berths: TideBerth[];
}
