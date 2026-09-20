# Deployment — Vercel (frontend) + Voroa (backend) + Supabase (PostgreSQL)

PortPulse AI ships as three deployable units:

```text
┌────────────────────────────┐         ┌─────────────────────────────────┐
│  Vercel — frontend (SPA)   │  /api/* │  Voroa — FastAPI web service    │
│  React + Vite build        │ ──────► │  uvicorn app.main:app           │
│  portpulse-ai.vercel.app   │ /health │      │                          │
└────────────────────────────┘         │      ▼                          │
                                       │  Supabase — managed PostgreSQL  │
                                       │  (pooler :6543 / direct :5432)  │
                                       └─────────────────────────────────┘
```

The Vercel deployment proxies `/api/*` and `/health` to the Voroa backend via
`src/frontend/vercel.json` rewrites, so the browser only ever talks to one origin —
no CORS configuration is required, and the relative-path API client
(`src/frontend/src/lib/api.ts`) works unchanged.

The backend **self-bootstraps**: on startup it creates the schema, seeds the REAL POLB
reference data + the `DEMO_AIS` simulation layer if the database is empty, and refreshes
the tides/weather pipelines and the data-quality pass (`src/backend/app/main.py` lifespan).
No manual seed step is needed on a fresh database, though the first request can be slower.

Managed-Postgres URLs (`postgresql://…` / `postgres://…`) are normalised to the
psycopg3 driver (`postgresql+psycopg://…`) by `src/backend/app/db.py`.

---

## 1. Database on Supabase (done — provisioned)

A dedicated **portpulse-ai** Supabase project (ref `fxdclkjneuoelggoralu`, region
`ap-south-1`) is already provisioned and **fully seeded** (REAL POLB reference data +
DEMO_AIS simulation layer). The app role is `portpulse_app`; its credentials live in
the Voroa environment variables — never in the repository.

For a **new** Supabase project instead:

1. Create the project (free tier, region close to the backend).
2. Create the app role with DDL rights on `public` (see `docs/deployment.md` history
   or run the backend seed once as `postgres`), then set `DATABASE_URL` to the
   **session pooler** string — username must carry the project ref:
   `postgresql+psycopg://<user>.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require`
3. The backend self-seeds an empty database on startup (`--reset` wipes and re-seeds).

> ⚠️ Supabase free-tier projects **pause after ~7 days of inactivity**; the deployed
> backend keeps it active while it runs. Restore a paused project from the dashboard.

### 1.2 Create the web service

1. **Connect GitHub** and grant Voroa access to `Aryan-B-Parikh/404-Team-Not-Found`.
2. **New service → Web service**, pick the repository and the `main` branch.
3. Set the **Root directory** to `src/backend` if the dashboard offers one; otherwise
   prefix the commands below with `cd src/backend && `.
4. Build and start commands (Python 3.11):

   ```bash
   # Build command
   pip install --upgrade pip && pip install -e .

   # Start command (reads $PORT from the platform)
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

   > `pip install -e .` installs from `src/backend/pyproject.toml`. If Voroa has a
   > Python version selector, choose **3.11** (`requires-python = "==3.11.*"`).

5. **Environment variables**:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | `postgresql+psycopg://portpulse_app.<ref>:<password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require` (Supabase session pooler; username carries the project ref) |
   | `DB_PGBOUNCER` | `true` only for the transaction pooler `:6543` (disables prepared statements); not needed on `:5432` |
   | `DB_SSL` | `true` (or rely on the `sslmode=require` in the URL) |
   | `PORT` | leave unset — Voroa injects it; the start command reads it |
   | `CORS_ORIGINS` | `https://<your-vercel-domain>` (harmless with the proxy, correct if you ever call the API cross-origin) |
   | `LLM_PROVIDER` | `auto` |
   | `BOB_API_KEY` | set only if the IBM Bob agent mode is available on the host (the `bob` CLI must also be installed); without it the app uses the deterministic engine-grounded fallback |
   | `SIM_SEED` | `20240817` (reproducible demo dataset) |
   | `FEATURE_WEATHER` / `FEATURE_QUALITY` / `FEATURE_UPLOAD` / `FEATURE_TIDAL` / `FEATURE_INCREMENTAL` / `FEATURE_SCENARIOS_EXT` | `true` |

6. **Health check path**: `/health` — the app exposes it and only answers once the
   startup bootstrap (schema/seed/pipelines) is done. If the first deploy exceeds the
   startup window, raise **Startup timeout** in Settings (the seeding + LightGBM
   warm-up can take a couple of minutes on a cold host).
7. **Deploy.** Watch the build log; on success the service is live at
   `https://<service-name>.getvoroa.com`.
8. Verify: open `https://<service-name>.getvoroa.com/health` → `{"status": "ok"}`,
   then `…/api/overview` → live KPI JSON. The startup log should show
   `[startup] operational dataset: DEMO_AIS (…)`.
9. Turn on **auto-deploy** so pushes to `main` ship automatically.

> ⚠️ **Cold starts are real.** The first forecast/optimise call after a deploy trains
> LightGBM and solves CP-SAT (~11 s forecast, ~20–30 s full plan). Warm/cached requests
> are ~1 s. Prewarm by opening the dashboard once before a demo.

### 1.3 Bob / MCP on the deployed backend (optional)

The MCP server (`src/backend/app/mcp_server.py`) is registered with IBM Bob from the
developer machine via `.bob/mcp.json`, which points at a local `uv` command. A deployed
Bob integration needs Bob to reach a publicly reachable MCP endpoint (e.g. an HTTP/SSE
transport) — that is a Phase-2 item. The dashboard's Bob surface will use the
deterministic engine-grounded fallback on Voroa unless the `bob` CLI and key are
available on the host. This is stated honestly in `IMPLEMENTATION_STATUS.md` and
`submission.yaml`.

---

## 2. Frontend on Vercel

1. **Add New… → Project** in Vercel, import `Aryan-B-Parikh/404-Team-Not-Found`.
2. Configure the project:
   - **Root Directory**: `src/frontend`
   - **Framework Preset**: Vite (Vercel auto-detects; `vercel.json` pins the commands)
   - **Build Command**: `npm run build` · **Output**: `dist`
3. **Before the first deploy**, edit `src/frontend/vercel.json` and replace
   `PORTPULSE-BACKEND-URL` (2 occurrences) with your Voroa service name from step 1,
   e.g. `https://portpulse-api.getvoroa.com`. Commit and push — Vercel redeploys.
4. Deploy. The SPA is served at `https://<project>.vercel.app`; deep links
   (`/berth`, `/forecast`, …) are rewritten to `index.html`, and `/api/*` + `/health`
   are proxied to Voroa.
5. Verify: open the dashboard, check the Overview KPIs are **live numbers**, then ask
   Bob: *"What's the biggest operational risk over the next 72 hours?"*
6. Update the deployment metadata:
   - `demo/live-demo-url.txt` → the Vercel URL (replacing "NOT DEPLOYED")
   - `submission.yaml` → `live_demo:` field

---

## 3. Post-deploy checklist

- [ ] `https://<voroa>.getvoroa.com/health` returns `{"status": "ok"}`
- [ ] `/api/overview` returns live engine data (not stubs)
- [ ] Vercel dashboard renders the same KPI values through the proxy
- [ ] Forecast tab shows quantile bands; Berth & Cranes shows the CP-SAT vs FIFO delta
- [ ] Scenario run + rollback works (`POST /api/scenarios/extended` → `/rollback`)
- [ ] Weather badge present (Open-Meteo reachable from the host)
- [ ] `demo/live-demo-url.txt` + `submission.yaml` updated
- [ ] Bob status: `GET /api/bob/status` shows the expected provider/fallback mode

## 4. Cost / plan notes

- **Supabase free tier** hosts the database ($0/month; the project is already seeded).
- **Voroa** hosts the FastAPI web service; the free default address (`*.getvoroa.com`)
  includes HTTPS. Idle/sleep behaviour and plan limits are set in the Voroa dashboard —
  for a demo, disable sleeping so the first judge request is not a cold start.
- Vercel's Hobby plan serves the SPA and the rewrites used here; no serverless
  functions are involved, so no function-timeout tuning is needed.

## 5. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Deploy aborted — "not ready within 180s" | First boot seeds the DB; raise **Startup timeout** (Settings) to ~300 s and set Health check path to `/health`. |
| `/api/*` returns 504 from Vercel | Long CP-SAT solve. Retry once (warm cache) or prewarm with `GET /api/overview` before the demo. |
| `Can't load plugin: sqlalchemy.dialects:postgres` | `DATABASE_URL` scheme not recognised — the normaliser in `db.py` handles `postgresql://` and `postgres://`; make sure the var was saved and the service redeployed. |
| `no tenant identifier provided (external_id or sni_hostname required)` | Supabase pooler URL missing the project ref in the username — use `<user>.<project-ref>@aws-0-<region>.pooler.supabase.com`. |
| `password authentication failed` for `portpulse_app` | Reset the role password (Supabase dashboard → SQL editor) and update the Voroa env var; the role is defined in the `create_portpulse_app_role` migration. |
| CORS errors in the browser console | You are calling the Voroa URL directly instead of through the Vercel proxy; use relative `/api` paths (the app already does). |
| Empty charts, "no congestion observations" | Database emptied; redeploy the backend (startup re-seeds only when `terminal` is empty) or run the seed command once. |
