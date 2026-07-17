@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI USB Commissioning Phase 1 - Guarded Rollback
set "ROOT=%~dp0.."
set "PY=%ROOT%\env\python\python.exe"
if not exist "%PY%" (
  echo STOPPED FAIL-CLOSED: bundled Python is missing.
  pause
  exit /b 2
)
"%PY%" "%~dp0rollback_usb_commissioning_phase1.py"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
