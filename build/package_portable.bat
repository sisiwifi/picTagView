@echo off
setlocal
title picTagView Portable Packager

set "SCRIPT_DIR=%~dp0"

if defined PORTABLE_PYTHON_DIR (
  set "RUNTIME_DIR=%PORTABLE_PYTHON_DIR%"
) else if exist "%SCRIPT_DIR%runtime\python\python.exe" (
  set "RUNTIME_DIR=%SCRIPT_DIR%runtime\python"
) else (
  set "RUNTIME_DIR="
)

if exist "%SCRIPT_DIR%..\.venv\Scripts\python.exe" (
  set "PYTHON_EXE=%SCRIPT_DIR%..\.venv\Scripts\python.exe"
) else (
  set "PYTHON_EXE=python"
)

if defined PORTABLE_BACKEND_PROTECTION (
  set "BACKEND_PROTECTION=%PORTABLE_BACKEND_PROTECTION%"
) else (
  set "BACKEND_PROTECTION=pyc"
)

echo.
echo Portable ZIP packaging is ready.
echo Make sure the project files are ready before continuing.
echo Press any key to start packaging...
pause >nul

echo.
echo Packaging in progress. Please keep this window open...
echo.

if defined RUNTIME_DIR (
  "%PYTHON_EXE%" "%SCRIPT_DIR%package_portable.py" --backend-protection "%BACKEND_PROTECTION%" --runtime-python-dir "%RUNTIME_DIR%"
) else (
  "%PYTHON_EXE%" "%SCRIPT_DIR%package_portable.py" --backend-protection "%BACKEND_PROTECTION%"
)

set "PACK_EXIT=%ERRORLEVEL%"

echo.
if "%PACK_EXIT%"=="0" (
  echo Packaging completed.
) else (
  echo Packaging failed. Exit code: %PACK_EXIT%
  echo Check the output above for the exact error.
)
echo Press any key to close this window...
pause >nul

endlocal & exit /b %PACK_EXIT%