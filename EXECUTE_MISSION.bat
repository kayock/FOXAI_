@echo off
setlocal
title FOXAI Mission Execution Engine

cd /d "%~dp0"

echo ==========================================
echo FOXAI Mission Execution Engine
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" EXECUTE_MISSION.py %*
) else (
    python EXECUTE_MISSION.py %*
)

echo.
pause
