@echo off
setlocal
title FOXAI Bridge Command

cd /d "%~dp0"

echo ==========================================
echo FOXAI Bridge Command
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" BRIDGE_COMMAND.py %*
) else (
    python BRIDGE_COMMAND.py %*
)

echo.
pause
