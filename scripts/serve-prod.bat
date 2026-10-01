@echo off
REM Production-style single server on Windows (waitress). Needs DEBUG=False, SECRET_KEY, ALLOWED_HOSTS in .env
cd /d %~dp0\..
call .venv\Scripts\activate.bat
cd frontend && call npm run build && cd ..
python backend\manage.py migrate --noinput
python backend\manage.py collectstatic --noinput
cd backend && waitress-serve --listen=0.0.0.0:8000 config.wsgi:application
