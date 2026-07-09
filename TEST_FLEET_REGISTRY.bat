@echo off
setlocal
title FOXAI CM v2.3 Fleet Registry

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v2.3 Fleet Registry
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_FLEET_REGISTRY.py
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 TEST_FLEET_REGISTRY.py
    ) else (
        python TEST_FLEET_REGISTRY.py
    )
)

echo.
pause
