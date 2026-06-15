#!/usr/bin/env bash
# Production run: multiple async workers (handles hundreds of concurrent users).
# Usage: ./run.sh [PORT]
set -e
cd "$(dirname "$0")"

PORT="${1:-8000}"
export BIND="0.0.0.0:${PORT}"

# Activate venv if present.
if [ -f "../venv/bin/activate" ]; then source ../venv/bin/activate; fi

echo "Starting Knowledge Graph API on http://localhost:${PORT}"
echo "Workers: ${WEB_CONCURRENCY:-auto}  |  open http://localhost:${PORT} in your browser"
exec gunicorn -c gunicorn_conf.py main:app
