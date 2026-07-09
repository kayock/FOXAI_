@echo off
setlocal
title FOXAI Mission Planner v3.1 Intent Engine

cd /d "%~dp0"

echo ==========================================
echo FOXAI Mission Planner v3.1 Intent Engine
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_INTENT_ENGINE.py
) else (
    python TEST_INTENT_ENGINE.py
)

echo.
pause
