@echo off
setlocal
title FOXAI CM v4.0 Fleet Command Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v4.0 Fleet Command Test
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_FLEET_COMMAND.py
) else (
    python TEST_FLEET_COMMAND.py
)

echo.
pause
