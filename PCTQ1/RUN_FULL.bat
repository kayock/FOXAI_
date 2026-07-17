@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PsyLLM Creative Quality FULL

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
echo FULL MODE
echo.
echo Close FOXAI WebUI, Chat Engine, and benchmark servers first.
echo This benchmark is isolated and makes no live source changes.
echo It may take several minutes.
echo.

if not defined PY (
  echo ERROR: Python was not found.
  echo Extract the complete PCTQ1 folder directly inside Z:\FOXAI.
  pause
  exit /b 1
)

call "%PY%" %ARGS% "%~dp0bench.py" full
set "RC=%ERRORLEVEL%"
echo.
echo Benchmark exit code: %RC%
if not "%RC%"=="0" pause
exit /b %RC%
