@echo off
setlocal
title FOXAI CM v2.3b Lifecycle Guard Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v2.3b Lifecycle Guard Test
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_NO_LAUNCH_LIFECYCLE_GUARD.py
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 TEST_NO_LAUNCH_LIFECYCLE_GUARD.py
    ) else (
        python TEST_NO_LAUNCH_LIFECYCLE_GUARD.py
    )
)

echo.
pause
