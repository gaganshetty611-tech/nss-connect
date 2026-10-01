#!/usr/bin/env bash
# Production-style single server: builds the React app and serves SPA + API from Django on :8000.
# Requires DEBUG=False, SECRET_KEY and ALLOWED_HOSTS in .env (add .trycloudflare.com for tunnels).
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
(cd frontend && npm run build)
python backend/manage.py migrate --noinput
python backend/manage.py collectstatic --noinput
cd backend && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --access-logfile -
