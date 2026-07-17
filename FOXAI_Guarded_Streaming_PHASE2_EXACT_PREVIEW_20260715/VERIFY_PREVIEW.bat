@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI Guarded Streaming Phase 2 Exact Preview

set "PY="
set "ARGS="
if exist "..\env\python\python.exe" (
  set "PY=..\env\python\python.exe"
) else if exist "..\python\python.exe" (
  set "PY=..\python\python.exe"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    set "PY=py"
    set "ARGS=-3"
  ) else (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
  )
)

if not defined PY (
  echo ERROR: Python was not found.
  pause
  exit /b 1
)

call "%PY%" %ARGS% "%~dp0verify_preview.py"
exit /b %ERRORLEVEL%
