@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI Qwen3VL Official Vision Projector

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
echo FOXAI OFFICIAL QWEN3VL Q8 VISION PROJECTOR
echo.
echo This downloads one pinned model-support file from the official Qwen
echo Hugging Face repository and verifies its SHA-256 before installation.
echo No FOXAI source or configuration file is modified.
echo.

if not defined PY (
  echo ERROR: Python was not found.
  echo Extract the complete MMQ8A folder directly inside Z:\FOXAI.
  pause
  exit /b 1
)

call "%PY%" %ARGS% "%~dp0install.py"
set "RC=%ERRORLEVEL%"

echo.
echo Installer exit code: %RC%
if not "%RC%"=="0" pause
exit /b %RC%
