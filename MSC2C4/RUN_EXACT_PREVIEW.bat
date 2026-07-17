@echo off
setlocal
title FOXAI Model Status Clarity Phase 2C4 - Exact Preview
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

echo ========================================================================
echo FOXAI MODEL STATUS CLARITY PHASE 2C4
echo EXACT PREVIEW - NO LIVE CHANGES
echo ========================================================================
echo.
echo Proposed display:
echo   Engine: RUNNING or STOPPED
echo   Model source: USB, HOST PC, LAN, or ONLINE PROVIDER
echo   Network use: NONE, LAN, or INTERNET
echo.
echo This preview does not modify FOXAI, models, registry, or launcher.
echo.

if not exist "%PYTHON%" (
  echo [STOPPED] FOXAI bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -s "%~dp0run_exact_preview.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Phase 2C4 exact preview completed.
) else (
  echo [STOPPED] Exact preview failed closed.
)
echo.
pause
exit /b %RESULT%
