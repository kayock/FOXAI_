@echo off
setlocal
title FOXAI Restore Extension Health Arbiter

cd /d "%~dp0"

echo ==========================================
echo FOXAI Restore Extension Health Arbiter
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" RESTORE_EXTENSION_HEALTH_ARBITER.py
) else (
    python RESTORE_EXTENSION_HEALTH_ARBITER.py
)

echo.
pause
