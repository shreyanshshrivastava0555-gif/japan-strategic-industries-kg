#!/usr/bin/env bash
# Development run: single worker with auto-reload.
# Usage: ./run_dev.sh [PORT]
set -e
cd "$(dirname "$0")"

PORT="${1:-8000}"
if [ -f "../venv/bin/activate" ]; then source ../venv/bin/activate; fi

echo "Dev server on http://localhost:${PORT} (auto-reload)"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}" --reload
