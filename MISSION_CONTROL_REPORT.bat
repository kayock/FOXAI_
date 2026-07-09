@echo off
setlocal
title FOXAI Mission Control Report

cd /d "%~dp0"

echo ==========================================
echo FOXAI Mission Control Report
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" MISSION_CONTROL_REPORT.py %*
) else (
    python MISSION_CONTROL_REPORT.py %*
)

echo.
pause
