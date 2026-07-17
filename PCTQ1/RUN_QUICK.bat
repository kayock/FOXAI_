@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PsyLLM Creative Quality QUICK

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

echo.
echo PSYLLM CREATIVE TEXT QUALITY BENCHMARK
echo QUICK MODE
echo.
echo Close FOXAI WebUI, Chat Engine, and benchmark servers first.
echo This runs fiction, dialogue, poetry, and story-hook tests.
echo.

if not defined PY (
  echo ERROR: Python was not found.
  echo Extract the complete PCTQ1 folder directly inside Z:\FOXAI.
  pause
  exit /b 1
)

call "%PY%" %ARGS% "%~dp0bench.py" quick
set "RC=%ERRORLEVEL%"
echo.
echo Benchmark exit code: %RC%
if not "%RC%"=="0" pause
exit /b %RC%
