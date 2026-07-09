@echo off
setlocal
title FOXAI CM v6.2 Service Contract Repair Patch

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v6.2 Service Contract Repair
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" PATCH_SERVICE_CONTRACTS.py
) else (
    python PATCH_SERVICE_CONTRACTS.py
)

echo.
pause
