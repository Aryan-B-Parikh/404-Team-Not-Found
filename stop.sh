#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN_DIR="${ROOT_DIR}/bin"
PGDATA="${ROOT_DIR}/pgdata"

echo "=== Stopping PortPulse AI Services ==="

echo "Stopping Vite frontend..."
pkill -f "vite --host" 2>/dev/null || true

echo "Stopping FastAPI backend..."
pkill -f "uvicorn app.main:app" 2>/dev/null || true

echo "Stopping PostgreSQL server..."
"${BIN_DIR}/pg_ctl" -D "${PGDATA}" stop 2>/dev/null || true

echo "=== All services stopped. ==="
