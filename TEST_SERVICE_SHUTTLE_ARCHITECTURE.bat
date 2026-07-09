@echo off
setlocal
title FOXAI CM v3.4b Service Shuttle Architecture Test
cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v3.4b Service Shuttle Architecture
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_SERVICE_SHUTTLE_ARCHITECTURE.py
) else (
    python TEST_SERVICE_SHUTTLE_ARCHITECTURE.py
)

echo.
pause
