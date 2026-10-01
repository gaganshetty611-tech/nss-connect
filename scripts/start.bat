@echo off
REM One-click start (Windows): sets everything up on first run, then launches API + web.
cd /d %~dp0\..
if not exist .env (copy .env.example .env >nul && powershell -Command "(Get-Content .env) -replace '^DEBUG=False','DEBUG=True' | Set-Content .env")
powershell -Command "if (-not (Select-String -Path .env -Pattern '^DEBUG=True' -Quiet)) { (Get-Content .env) -replace '^DEBUG=.*','DEBUG=True' | Set-Content .env }"
if not exist .venv (python -m venv .venv || goto :err)
call .venv\Scripts\activate.bat
if not exist .venv\.deps-ok (pip install -r backend\requirements.txt || goto :err & echo ok>.venv\.deps-ok)
python backend\manage.py migrate || goto :err
if not exist backend\db.sqlite3.seeded (python backend\manage.py seed_demo_data & echo ok>backend\db.sqlite3.seeded)
if not exist frontend\.env copy frontend\.env.example frontend\.env >nul
if not exist frontend\node_modules (cd frontend && npm install && cd ..)
start "NSS Connect API" cmd /k ".venv\Scripts\activate.bat && python backend\manage.py runserver 0.0.0.0:8000"
start "NSS Connect Web" cmd /k "cd frontend && npm run dev"
echo.
echo Backend check: http://127.0.0.1:8000/api/health/   App: http://localhost:5173
exit /b 0
:err
echo Setup failed - see the messages above.
pause
exit /b 1
