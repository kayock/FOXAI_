@echo off
setlocal
title FOXAI Host Model Library Phase 2C3 - Read-Only Validation
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

echo ========================================================================
echo FOXAI PORTABLE HOST MODEL LIBRARY PHASE 2C3
echo READ-ONLY PORTABILITY VALIDATION
echo ========================================================================
echo.
echo This validation does not start or stop a model.
echo It does not change the live registry, source, launcher, or model files.
echo State-changing scenarios use tiny temporary fixture files only.
echo.

if not exist "%PYTHON%" (
  echo [STOPPED] FOXAI bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -s "%~dp0validate_portability_phase2c3.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Phase 2C3 portability validation completed.
) else (
  echo [STOPPED] Validation failed closed. Read the printed report path.
)
echo.
pause
exit /b %RESULT%
