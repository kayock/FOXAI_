@echo off
setlocal
title FOXAI CM v3.7 Mission Executor Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v3.7 Mission Executor Test
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_MISSION_EXECUTOR.py
) else (
    python TEST_MISSION_EXECUTOR.py
)

echo.
pause
