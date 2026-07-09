@echo off
setlocal
title FOXAI CM v2.3a Safe Fleet Operations

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v2.3a Safe Fleet Operations
echo ==========================================
echo.
echo This prevents fleet health scans from launching GUI apps.
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" PATCH_SAFE_FLEET_OPERATIONS.py
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 PATCH_SAFE_FLEET_OPERATIONS.py
    ) else (
        python PATCH_SAFE_FLEET_OPERATIONS.py
    )
)

echo.
pause
