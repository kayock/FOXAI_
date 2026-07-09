@echo off
setlocal
title FOXAI Mission Planner v3.0

cd /d "%~dp0"

echo ==========================================
echo FOXAI Mission Planner v3.0
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_MISSION_PLANNER.py
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 TEST_MISSION_PLANNER.py
    ) else (
        python TEST_MISSION_PLANNER.py
    )
)

echo.
pause
