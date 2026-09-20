#!/usr/bin/env bash
# One-command dev stack (process audit rec #9 / backlog B-9).
#   scripts/dev.sh          → seed if empty, backend :8000, frontend :5173
#   scripts/dev.sh --reset  → wipe and reseed the demo dataset first
# Idempotent: skips servers already listening on their ports.

set -euo pipefail
cd "$(dirname "$0")/.."

PY="src/backend/.venv/Scripts/python.exe"      # Windows venv layout (this repo's checkout)
[ -f "$PY" ] || PY="src/backend/.venv/bin/python"
FE="src/frontend"

if [ "${1:-}" = "--reset" ]; then
  echo ">> reseeding database (--reset)"
  (cd src/backend && "$PY" -m app.seed --reset)
fi

port_busy() { netstat -ano 2>/dev/null | grep -E "[:.]$1 .*LISTEN" >/dev/null; }

if port_busy 8000; then
  echo ">> backend already running on :8000"
else
  echo ">> starting backend on :8000 (log: /tmp/uvicorn.log)"
  (cd src/backend && "$PY" -m uvicorn app.main:app --port 8000 > /tmp/uvicorn.log 2>&1 &)
fi

if port_busy 5173; then
  echo ">> frontend already running on :5173"
else
  echo ">> starting frontend on :5173 (log: /tmp/vite.log)"
  (cd "$FE" && npm run dev -- --port 5173 > /tmp/vite.log 2>&1 &)
fi

echo ">> waiting for health..."
for _ in $(seq 1 30); do
  if curl -sf -m 2 http://localhost:8000/health >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -s -m 5 http://localhost:8000/health && echo " ← backend" || echo "!! backend did not come up (see /tmp/uvicorn.log)"
echo ">> UI: http://localhost:5173/   API: http://localhost:8000/docs"
