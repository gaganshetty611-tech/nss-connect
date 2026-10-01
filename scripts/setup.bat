@echo off
REM One-time setup on Windows 10/11
cd /d %~dp0\..
if not exist .env (copy .env.example .env && powershell -Command "(Get-Content .env) -replace '^DEBUG=False','DEBUG=True' | Set-Content .env")
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r backend\requirements.txt
python backend\manage.py migrate
python backend\manage.py seed_demo_data
if not exist frontend\.env copy frontend\.env.example frontend\.env
cd frontend && npm install && cd ..
echo Done. Start with scripts\dev.bat
