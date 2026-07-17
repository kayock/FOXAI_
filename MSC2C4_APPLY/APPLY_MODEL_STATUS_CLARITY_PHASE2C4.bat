@echo off
setlocal
title FOXAI Model Status Clarity Phase 2C4 - Guarded Apply
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

if not exist "%PYTHON%" (
  echo [STOPPED] FOXAI bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -s "%~dp0apply_model_status_clarity_phase2c4.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Model Status Clarity Phase 2C4 is live.
) else (
  echo [STOPPED] Apply did not verify. Read the printed report path.
)
echo.
pause
exit /b %RESULT%
