# Contributing to PortPulse AI

## Development setup

Follow [`docs/setup-guide.md`](docs/setup-guide.md) for the full environment
(PostgreSQL, Python 3.11 via uv, Node ≥ 20). The short version:

```bash
./scripts/dev.sh            # seed if needed, start backend :8000 + frontend :5173
./scripts/dev.sh --reset    # wipe and reseed the demo dataset first
```

## Ground rules

- **Backend**: `ruff check app tests` must pass; add/adjust tests under
  `src/backend/tests/` for any behavior change. Tests marked `slow` run only
  in the full CI job — keep the fast tier fast.
- **Frontend**: `npm run typecheck` and `npm run build` must pass. Contract
  shapes live in `src/lib/contract.ts`, pinned to the generated types
  (`api-types.gen.ts`) — if you change a backend response model, re-export
  `openapi.json` and run `npm run gen:api`, then commit both.
- **No fabricated data**: every number shown in the UI must come from a real
  engine computation or a labelled dataset (`AIS` vs `DEMO_AIS`). This is the
  project's core principle — see `docs/solution-overview.md`.
- **GET endpoints stay read-only**: writes belong in POST refresh routes or
  the ingest pipelines.

## CI

`.github/workflows/validate.yml` runs on every push: lint + fast backend tests
+ typecheck + Playwright smoke tests + API contract drift check. PRs to
`main` additionally run the full backend suite (with a real Postgres service)
and the production build.
