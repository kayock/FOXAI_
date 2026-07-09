@echo off
setlocal
title FOXAI Stevedore Plugin Inspector

cd /d "%~dp0"

echo ==========================================
echo FOXAI Stevedore Plugin Inspector
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" STEVEDORE_INSPECTOR.py
) else (
    python STEVEDORE_INSPECTOR.py
)

echo.
pause
