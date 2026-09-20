import { defineConfig } from "@playwright/test";

// B-8: browser smoke tests in CI. Hermetic — API routes are mocked with fixtures
// that mirror the pinned contract shapes (src/lib/contract.ts), so no backend or
// database is needed, and a fixture/contract drift fails the suite loudly.
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --port 5173 --strictPort",
    url: "http://localhost:5173",
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
