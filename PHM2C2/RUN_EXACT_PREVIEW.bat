@echo off
setlocal
title FOXAI Host Model Library Phase 2C2 - Exact Preview
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"
if not exist "%PYTHON%" (
  echo [STOPPED] FOXAI bundled Python was not found.
  pause
  exit /b 2
)
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -s "%~dp0verify_exact_preview.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Phase 2C2 exact preview passed. No live files changed.
) else (
  echo [STOPPED] Exact preview failed closed. No live files changed.
)
echo.
pause
exit /b %RESULT%
