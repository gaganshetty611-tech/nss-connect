@echo off
REM Development on Windows: opens the API and the Vite dev server in two windows.
cd /d %~dp0\..
start "NSS Connect API" cmd /k ".venv\Scripts\activate.bat && python backend\manage.py runserver 0.0.0.0:8000"
start "NSS Connect Web" cmd /k "cd frontend && npm run dev"
