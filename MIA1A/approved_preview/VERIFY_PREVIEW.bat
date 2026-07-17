@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI Mission Image Attachments Phase 1 Exact Preview

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
echo FOXAI MISSION IMAGE ATTACHMENTS
echo PHASE 1 EXACT PREVIEW
echo.
echo This is a read-only verifier.
echo It contains no apply or install capability.
echo.

if not defined PY (
  echo ERROR: Python was not found.
  echo Extract the complete MIA1P folder directly inside Z:\FOXAI.
  pause
  exit /b 1
)

call "%PY%" %ARGS% "%~dp0verify_preview.py"
set "RC=%ERRORLEVEL%"

echo.
echo Verifier exit code: %RC%
if not "%RC%"=="0" pause
exit /b %RC%
