#!/usr/bin/env bash
# Start FastAPI with reload scoped to app/ only (uploads/ is never watched).
set -euo pipefail
cd "$(dirname "$0")"
exec uvicorn app.main:app --reload --reload-dir app --port 8000
