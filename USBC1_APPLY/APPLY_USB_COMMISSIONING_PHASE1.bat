@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI USB Commissioning Phase 1 - Guarded Apply
set "ROOT=%~dp0.."
set "PY=%ROOT%\env\python\python.exe"
if not exist "%PY%" (
  echo.
  echo STOPPED FAIL-CLOSED: bundled Python is missing.
  echo Expected: %PY%
  echo Nothing was changed.
  pause
  exit /b 2
)
"%PY%" "%~dp0apply_usb_commissioning_phase1.py"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
