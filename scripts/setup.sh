#!/usr/bin/env bash
# One-time setup: Python venv, backend deps, database + demo data, frontend deps.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { cp .env.example .env; sed -i.bak 's/^DEBUG=False/DEBUG=True/' .env && rm -f .env.bak; echo "Created .env (DEBUG=True)"; }
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py seed_demo_data || echo "(demo data already present – use: python backend/manage.py seed_demo_data --reset)"
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env
(cd frontend && npm install)
echo "Done. Start with: scripts/dev.sh"
