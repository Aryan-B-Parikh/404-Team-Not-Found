#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN_DIR="${ROOT_DIR}/bin"
PGDATA="${ROOT_DIR}/pgdata"

echo "=== PortFlow SBX Service Status ==="

# Database
if "${BIN_DIR}/pg_isready" -h "${PGDATA}" -p 5432 >/dev/null 2>&1; then
    echo "  [✓] PostgreSQL: RUNNING (Socket: ${PGDATA})"
else
    echo "  [✗] PostgreSQL: STOPPED"
fi

# Backend
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "  [✓] Backend API: RUNNING (http://localhost:8000)"
else
    echo "  [✗] Backend API: STOPPED"
fi

# Frontend
if curl -s http://localhost:5173 >/dev/null 2>&1; then
    echo "  [✓] Frontend Dashboard: RUNNING (http://localhost:5173)"
else
    echo "  [✗] Frontend Dashboard: STOPPED"
fi
echo "==================================="
