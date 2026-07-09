@echo off
setlocal
title FOXAI Captain's Log

cd /d "%~dp0"

echo ==========================================
echo FOXAI Captain's Log
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" CAPTAINS_LOG_VIEW.py
) else (
    python CAPTAINS_LOG_VIEW.py
)

echo.
pause
