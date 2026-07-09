@echo off
setlocal
title FOXAI Restore Service Contracts

cd /d "%~dp0"

echo ==========================================
echo FOXAI Restore Service Contracts
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" RESTORE_SERVICE_CONTRACTS.py
) else (
    python RESTORE_SERVICE_CONTRACTS.py
)

echo.
pause
