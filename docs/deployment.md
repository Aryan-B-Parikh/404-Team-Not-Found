# Deployment — Vercel (frontend + backend) + Supabase (PostgreSQL)

PortPulse AI ships as two deployable units, both on Vercel:

```text
┌───────────────────────────────┐  /api/*  ┌──────────────────────────────────┐
│  Vercel — frontend (SPA)      │ ───────► │  Vercel — FastAPI serverless fn  │
│  portpulse-ai-woad.vercel.app │  /health │  portpulse-api.vercel.app        │
└───────────────────────────────┘          │            │                     │
                                           │            ▼                     │
                                           │  Supabase — PostgreSQL 17        │
                                           │  (pooler :5432, sslmode=require) │
                                           └──────────────────────────────────┘
```

**Live:** frontend `https://portpulse-ai-woad.vercel.app` · backend
`https://portpulse-api.vercel.app` (`/api/health` → `{"status":"ok"}`).

The frontend proxies `/api/*` and `/health` to the backend via
`src/frontend/vercel.json` rewrites, so the browser only ever talks to one origin —
no CORS setup, and the relative-path API client (`src/frontend/src/lib/api.ts`)
works unchanged.

The backend connects to Supabase over the session pooler; managed-Postgres URL
schemes are normalised to psycopg3 in `src/backend/app/db.py`, and `DB_SSL=true`
forces `sslmode=require`. The database was provisioned and seeded out-of-band
(see §1); the backend also self-seeds an empty database on startup.

---

## 1. Database on Supabase (done — provisioned & seeded)

A dedicated **portpulse-ai** Supabase project (ref `fxdclkjneuoelggoralu`, region
`ap-south-1`, PostgreSQL 17) holds the data. The app role is `portpulse_app`
(created by the `create_portpulse_app_role` migration with DDL rights on
`public`); its credentials live only in the Vercel environment variables.

Connection string shape (note the **project ref in the username** — required by
Supavisor):

```
postgresql+psycopg://portpulse_app.<project-ref>:<password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require
```

> ⚠️ Supabase free-tier projects **pause after ~7 days of inactivity**; the running
> backend keeps this one active. Restore a paused project from the Supabase dashboard.

To re-seed from a machine with the repo: run `python -m app.seed --reset` in
`src/backend` with `DATABASE_URL` set to the pooler string above (username must
include the project ref). The backend also auto-seeds an empty database on startup.

---

## 2. Backend on Vercel (serverless Python function)

Deployed via CLI from `src/backend`: `vercel link --project portpulse-api`, then
`vercel deploy --prod`. Key facts:

- **Entry point** `src/backend/api/index.py` exposes the FastAPI `app`; Vercel's
  Python builder routes `/api/*` to it natively. Do **not** add a catch-all
  rewrite to the function — Vercel replaces the ASGI scope path with the
  destination, and every route 404s (this cost us a debugging session).
- **`/health` is mirrored at `/api/health`** because only `/api/*` reaches the
  function; the frontend proxy targets `/health` at the backend's `/api/health`
  via its own rewrite of the same path shape.
- **`libgomp.so.1` is missing** in Vercel's Python runtime (LightGBM/sklearn need
  OpenMP). We vendor GCC-12's `libgomp.so.1` in `app/lib/` and preload it with
  `RTLD_GLOBAL` in `app/__init__.py` before any engine import.
- **Env vars** (production scope): `DATABASE_URL` (pooler string above),
  `DB_SSL=true`, `CORS_ORIGINS=https://portpulse-ai-woad.vercel.app`,
  `SIM_SEED=20240817`.
- **Performance:** the first cold request pays function boot + imports +
  LightGBM warm-up (~10–20 s; the forecast engine then trains from Supabase
  data). Warm requests are fast. Hobby-plan function cap is 2048 MB, and the
  builder runs Python 3.12 — so `pyproject.toml` uses `requires-python = ">=3.11"`
  (do not re-pin `==3.11.*`; the builder has no 3.11).

---

## 3. Frontend on Vercel (SPA)

Deployed via CLI from `src/frontend` (`vercel link --project portpulse-ai`,
`vercel deploy --prod`), or by importing the repo in the Vercel dashboard with
**Root Directory: `src/frontend`**. `src/frontend/vercel.json` pins the Vite
build (`npm run build` → `dist`) and the rewrites:

- `/health` → backend `/api/health`
- `/api/:path*` → backend `/api/:path*`
- everything else → `/index.html` (SPA deep links)

---

## 4. Post-deploy checklist

- [x] `https://portpulse-api.vercel.app/api/health` → `{"status":"ok"}`
- [x] `/api/overview` returns live engine data (DEMO_AIS + real POLB capacity)
- [x] Frontend SPA renders and proxies API calls (`/api/overview`, `/api/forecast`)
- [ ] Open the dashboard once before a demo to prewarm the engines
- [ ] `demo/live-demo-url.txt` + `submission.yaml` updated with the live URL

## 5. Cost / plan notes

- **Supabase free tier** hosts the database ($0/month, already seeded).
- **Vercel Hobby** hosts both the SPA and the serverless function (100 GB-h
  function execution included; Fluid Compute billing applies per active CPU).

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `FUNCTION_INVOCATION_FAILED` at boot, logs show `libgomp.so.1: cannot open shared object file` | The vendored preload didn't ship — check `app/lib/libgomp.so.1` is committed and `app/__init__.py` loads it before engine imports. |
| Every route returns FastAPI 404 (`{"detail":"Not Found"}`) even `/openapi.json` | A catch-all rewrite to the function is mangling the ASGI path — remove rewrites from `src/backend/vercel.json` and rely on native `/api/*` routing. |
| `no tenant identifier provided (external_id or sni_hostname required)` | Supabase pooler URL missing the project ref in the username — use `<user>.<project-ref>@aws-0-<region>.pooler.supabase.com`. |
| `npm error ENOENT … /vercel/path0/package.json` in Git-driven builds | A project is building the repo root with Node defaults. Set **Root Directory** (`src/frontend` / `src/backend`) per project in the Vercel dashboard, or deploy via CLI from those directories as this guide does. |
| 503/504 on first request after idle | Cold start + engine warm-up. Prewarm with `GET /api/overview` before the demo. |
| Builder error: `No interpreter found for Python 3.11` | `requires-python` was re-pinned to `==3.11.*` or a `.python-version` file says 3.11 — the Vercel builder only has 3.12; keep `>=3.11`. |
| CORS errors in the browser console | Calling the backend URL directly instead of through the frontend proxy; use relative `/api` paths (the app already does). |
