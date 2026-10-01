@echo off
REM Expose the app to any phone via Cloudflare quick tunnel (HTTPS). Usage: share-mobile.bat [port]
set PORT=%1
if "%PORT%"=="" set PORT=5173
where cloudflared >nul 2>nul && (cloudflared tunnel --url http://localhost:%PORT% & goto :eof)
where ngrok >nul 2>nul && (ngrok http %PORT% & goto :eof)
echo Install cloudflared: winget install --id Cloudflare.cloudflared   (or ngrok from https://ngrok.com/download)
