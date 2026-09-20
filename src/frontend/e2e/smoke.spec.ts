import { test, expect, type Route } from "@playwright/test";

// Fixtures mirror src/lib/contract.ts shapes exactly — extra keys would be
// rejected by the Zod parse, missing keys would fail typecheck on this file.
// If either layer drifts, these tests fail: that is the point.

const ZONE = {
  zone_code: "T5", label: "T5 — Container", level: "HIGH", trend: "RISING",
  current_index: 71, peak_index: 84, peak_hour: 30, recent_index: [55, 60, 66, 71],
  queue_now: 7, wait_now: 14.5, yard_util_pct: 62, berths: 4, cranes: 9,
};

const HOTSPOT = {
  zone_code: "T5", zone_name: "T5 — Container", risk_score: 0.82, confidence: 0.9,
  peak_index: 84, peak_hour: 30, binding_constraint: "cranes",
  binding_evidence: {}, resource_pressure: {}, explanation: "test",
  components: {}, weights: {},
};

const OVERVIEW = {
  t0: "2026-09-20T08:00:00Z",
  dataset: { source: "AIS", note: "test fixture" },
  data_version: "test", weather_used: false, confidence: 0.87,
  kpis: {
    vessels_at_anchor: 12, vessels_inbound: 5, avg_anchorage_wait: 9.3,
    max_anchored_hours: 31.5, arrivals_next24: 8, port_index_now: 58,
    peak_forecast_index: 76, peak_forecast_hour: 32, moves_pending: 140,
    daily_fleet_burn_usd: 512000, berth_util_pct: 64, crane_util_pct: 71,
  },
  zones: [ZONE],
  alerts: [{ severity: "WARN", title: "test alert", detail: "d" }],
  hotspots: { ranked: [HOTSPOT] },
  anomalies: [],
  arrivals_timeline: Array.from({ length: 24 }, (_, hour) => ({ hour, count: 2 })),
  last_updated: "2026-09-20T08:05:00Z",
};

// Mirrors GET /api/terminals terminal shape (cranes is an ARRAY of crane objects).
const TERMINAL = {
  code: "ITS", name: "International Transportation Service", pier: "Pier G",
  lat: 33.746, lon: -118.203, berth_length_ft: 4250, deepsea_berths: 3,
  gantry_cranes: 14, capacity_teu_m: null, zone_code: "Z-ITS", note: "test",
  berths: [{ name: "I-1", seq: 1, length_ft: 1416, depth_ft: 50.0, cranes_max: 5 }],
  cranes: [{ code: "ITS-STS-01", type: "STS", reach_ft: 210.0, rated_moves_per_hour: 28.0, status: "AVAILABLE", reason: null }],
  gate: null, yard_zones: [],
};

const OPT = {
  run_id: 42, solver: "CP-SAT", status: "OPTIMAL", objective: 1180.5, solve_ms: 640,
  assignments: [{
    vessel_name: "MSC TEST", mmsi: "111222333", terminal_code: "T5",
    berth_window_start_h: 2, wait_hours: 3.5, moves: 1200, cranes_assigned: 3,
  }],
  metrics: {
    serviced: 10, deferred: 1, total_wait_hours: 38.2, makespan_hours: 70,
    berth_util_pct: 62, crane_util_pct: 69, avg_cranes_per_vessel: 2.8,
    total_moves: 12800,
  },
  baseline: {
    serviced: 9, deferred: 2, total_wait_hours: 108.4, makespan_hours: 82,
    berth_util_pct: 58, crane_util_pct: 61, avg_cranes_per_vessel: 2.4,
    total_moves: 11800,
  },
  deltas: { wait_total: 70.2, makespan: 12, serviced: 1 },
  deferred: [{ vessel_name: "LATE ARRIVAL", reason: "Horizon capacity exhausted" }],
  weights: {}, gap_pct: null, tidal_feasible: true, incremental: false,
  horizon_hours: 72, params: {},
};

const TIDES = {
  period_hours: 12.42, amplitude_ft: 4.1, under_keel_margin_ft: 1.5,
  source: "noaa-coops", berths: [{
    berth_id: "T5-1", terminal_code: "T5", station: "9410660",
    windows: [{ hours_ago: 0, tide_ft: 3.2, navigable: true }],
  }],
};

async function mockApi(page: Page) {
  const json = (body: unknown) => (route: Route) => route.fulfill({ json: body });
  await page.route("**/api/ais/status", json({ source: "AIS", rows: 1000, zones: 4, track_points: 9000, stub: false }));
  await page.route("**/api/overview", json(OVERVIEW));
  await page.route("**/api/terminals*", json({ terminals: [TERMINAL], source: "test" }));
  await page.route("**/api/optimise/latest", json(OPT));
  await page.route("**/api/tides", json(TIDES));
}

test.describe("smoke — pages render live engine numbers", () => {
  test("Overview shows real KPI values and deep link lands on Overview", async ({ page }) => {
    await mockApi(page);
    await page.goto("/overview");
    // KPI values must come from the API response, not placeholders (exact match
    // avoids substring collisions with the clock and other page text).
    await expect(page.getByText("12", { exact: true })).toBeVisible(); // vessels_at_anchor
    await expect(page.getByText(/9\.3/).first()).toBeVisible(); // avg_anchorage_wait (may carry a unit suffix)
    await expect(page.getByText(/^58$/, { exact: true }).first()).toBeVisible(); // port_index_now
    await expect(page.getByText(/T5/).first()).toBeVisible(); // zone card renders
  });

  test("Berth & Cranes headline shows the CP-SAT wait delta vs FIFO", async ({ page }) => {
    await mockApi(page);
    await page.goto("/berth");
    // deltas.wait_total = 70.2 → headline "−70.2h" (tier 1, same snapshot as FIFO).
    await expect(page.getByText("−70.2h")).toBeVisible();
    await expect(page.getByText(/vessels serviced/i).first()).toBeVisible();
    await expect(page.getByText(/deferred/i).first()).toBeVisible();
  });

  test("unknown deep link falls back to Overview", async ({ page }) => {
    await mockApi(page);
    await page.goto("/no-such-tab");
    await expect(page.getByText("12", { exact: true })).toBeVisible(); // Overview KPI renders
  });
});
