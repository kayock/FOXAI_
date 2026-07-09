@echo off
setlocal
title FOXAI Fleet Command

cd /d "%~dp0"

echo ==========================================
echo FOXAI Fleet Command
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" FLEET_COMMAND.py %*
) else (
    python FLEET_COMMAND.py %*
)

echo.
pause
