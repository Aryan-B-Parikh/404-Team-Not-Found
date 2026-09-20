<!-- Title convention: `area: change` (e.g. `forecast: fix weather sign convention`) -->

## What & why

<!-- One or two sentences. Link the tracking item from docs/backlog.md if one exists. -->

## Verification

<!-- How you proved it works: test names, commands run, or the tab/endpoint you exercised. -->

- [ ] `pytest -m "not slow"` passes locally (~3s)
- [ ] Full suite green if engines/DB touched (`pytest`, ~3 min)
- [ ] `npm run typecheck` passes if `src/frontend` touched

## Contract check

<!-- If this PR renames/moves any API field, both sides must change in the same PR.
     The tripwire tests in tests/test_contract_drift.py enforce the known pins. -->

- [ ] No API field renamed, **or** `src/backend/openapi.json` re-exported + `src/frontend/src/lib/api-types.gen.ts` regenerated in the same PR (CI fails on drift); if `/api/overview` changed, `src/frontend/src/lib/contract.ts` too
