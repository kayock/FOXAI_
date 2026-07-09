@echo off
setlocal
title FOXAI Engineering Department Status

cd /d "%~dp0"

echo ==========================================
echo FOXAI Engineering Department Status
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" ENGINEERING_STATUS.py
) else (
    python ENGINEERING_STATUS.py
)

echo.
pause
