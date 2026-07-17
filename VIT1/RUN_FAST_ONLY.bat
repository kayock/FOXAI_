@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI Vision Input Test - Fast Vision

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
echo FOXAI REAL QWEN3VL IMAGE-INPUT TEST
echo Mode: FAST
echo.
echo Close FOXAI WebUI, Chat Engine, and all benchmark servers first.
echo This sends real PNG image bytes to the local vision model.
echo No live source, configuration, archive, or security log is changed.
echo.

if not defined PY (
  echo ERROR: Python was not found.
  echo Extract the complete VIT1 folder directly inside Z:\FOXAI.
  pause
  exit /b 1
)

call "%PY%" %ARGS% "%~dp0vision_test.py" fast
set "RC=%ERRORLEVEL%"
echo.
echo Vision test exit code: %RC%
if not "%RC%"=="0" pause
exit /b %RC%
