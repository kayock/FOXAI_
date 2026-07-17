@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI USB Commissioning Phase 1 Exact Preview

set "PY=..\env\python\python.exe"
if not exist "%PY%" (
  echo Bundled Python was not found at %PY%
  echo Extract the complete USBC1P folder directly inside the FOXAI root.
  pause
  exit /b 1
)

"%PY%" "%~dp0verify_preview.py"
exit /b %ERRORLEVEL%
