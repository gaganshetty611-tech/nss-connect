#!/usr/bin/env bash
# Expose the running app to ANY phone on ANY network via a free Cloudflare quick tunnel (HTTPS).
# Run scripts/dev.sh (or serve-prod.sh) first. Usage: scripts/share-mobile.sh [port]
#   port 5173 = Vite dev server (default)   port 8000 = Django serving the production build
set -euo pipefail
PORT="${1:-5173}"
if command -v cloudflared >/dev/null 2>&1; then
  echo "Starting Cloudflare tunnel to http://localhost:$PORT – open the https://*.trycloudflare.com URL on your phone."
  exec cloudflared tunnel --url "http://localhost:$PORT"
elif command -v ngrok >/dev/null 2>&1; then
  echo "cloudflared not found; using ngrok."
  exec ngrok http "$PORT"
else
  echo "Install cloudflared (https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) or ngrok (https://ngrok.com/download)."
  exit 1
fi
