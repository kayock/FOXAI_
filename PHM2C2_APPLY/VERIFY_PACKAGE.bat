@echo off
setlocal
title FOXAI Host Model Library Phase 2C2 - Verify Guarded Apply
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"
if not exist "%PYTHON%" (
  echo [STOPPED] Bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -s "%~dp0verify_package.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Guarded apply package is ready.
) else (
  echo [STOPPED] Package verification failed closed.
)
echo.
pause
exit /b %RESULT%
