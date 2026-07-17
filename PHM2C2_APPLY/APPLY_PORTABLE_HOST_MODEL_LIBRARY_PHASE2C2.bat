@echo off
setlocal
title FOXAI Host Model Library Phase 2C2 - Guarded Apply
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
"%PYTHON%" -s "%~dp0apply_host_model_phase2c2.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Portable Host Model Library Phase 2C2 is live.
) else (
  echo [STOPPED] Apply did not verify. Read the printed report path.
)
echo.
pause
exit /b %RESULT%
