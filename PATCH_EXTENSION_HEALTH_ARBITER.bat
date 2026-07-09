@echo off
setlocal
title FOXAI CM v3.6 Extension Health Arbiter Patch

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v3.6 Extension Health Arbiter
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" PATCH_EXTENSION_HEALTH_ARBITER.py
) else (
    python PATCH_EXTENSION_HEALTH_ARBITER.py
)

echo.
pause
