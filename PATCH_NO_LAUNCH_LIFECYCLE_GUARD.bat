@echo off
setlocal
title FOXAI CM v2.3b No-Launch Lifecycle Guard

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v2.3b No-Launch Lifecycle Guard
echo ==========================================
echo.
echo This makes Fleet Registry refresh passive-only.
echo Health scans will not call plugin hooks or launch apps.
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" PATCH_NO_LAUNCH_LIFECYCLE_GUARD.py
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 PATCH_NO_LAUNCH_LIFECYCLE_GUARD.py
    ) else (
        python PATCH_NO_LAUNCH_LIFECYCLE_GUARD.py
    )
)

echo.
pause
