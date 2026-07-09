@echo off
setlocal
title FOXAI Project Orion v7.3 Event Bus Demo

cd /d "%~dp0"

echo ==========================================
echo FOXAI Project Orion v7.3 Event Bus Demo
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" EVENT_BUS_DEMO.py
) else (
    python EVENT_BUS_DEMO.py
)

echo.
pause
