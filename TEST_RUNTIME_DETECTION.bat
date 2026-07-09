@echo off
setlocal
title FOXAI CM v5.2 Hangar Bay Package Inspector

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v5.2 Hangar Bay Package Inspector
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_RUNTIME_DETECTION.py
) else (
    python TEST_RUNTIME_DETECTION.py
)

echo.
pause
