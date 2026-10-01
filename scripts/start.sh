#!/usr/bin/env bash
# One-click start (macOS/Linux): first-run setup, then API + web together.
set -e
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
grep -q '^DEBUG=True' .env || sed -i.bak 's/^DEBUG=.*/DEBUG=True/' .env
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
[ -f .venv/.deps-ok ] || { pip install -r backend/requirements.txt && touch .venv/.deps-ok; }
python backend/manage.py migrate
[ -f backend/db.sqlite3.seeded ] || { python backend/manage.py seed_demo_data || true; touch backend/db.sqlite3.seeded; }
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env
[ -d frontend/node_modules ] || (cd frontend && npm install)
trap 'kill 0' EXIT
python backend/manage.py runserver 0.0.0.0:8000 &
(cd frontend && npm run dev) &
wait
