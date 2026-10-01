#!/usr/bin/env bash
# Development: Django API on :8000 + Vite on :5173 (Vite proxies /api and /media to Django).
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
python backend/manage.py runserver 0.0.0.0:8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT
cd frontend && npm run dev
