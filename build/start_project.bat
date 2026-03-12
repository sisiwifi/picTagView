@echo off
setlocal

echo Starting backend...
echo If you want Docker, run: docker compose up --build
start "picTagView-backend" cmd /k "cd /d %~dp0..\backend && python -m uvicorn app.main:app --reload"

echo Waiting for backend to initialize...
timeout /t 2 /nobreak >nul

echo Checking backend health: http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/ >nul 2>&1
if %errorlevel%==0 (
  echo Backend is running.
) else (
  echo Backend may still be starting. Please wait a few seconds and refresh.
)

echo Starting frontend...
start "picTagView-frontend" cmd /k "cd /d %~dp0..\frontend && npm run serve"

echo All components started.
endlocal
