@echo off
setlocal

echo Starting backend...
echo If you want Docker, run: docker compose up --build
set "BACKEND_PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%BACKEND_PY%" (
  echo Project virtual environment not found: %BACKEND_PY%
  echo Run backend\requirements.txt installation first, or create .venv at the repo root.
  exit /b 1
)
start "picTagView-backend" cmd /k "cd /d %~dp0..\backend && %BACKEND_PY% -m uvicorn app.main:app --reload"

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
