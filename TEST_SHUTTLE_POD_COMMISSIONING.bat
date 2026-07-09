@echo off
setlocal
title FOXAI CM v2.2a Shuttle Pod Commissioning FIX

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v2.2a Shuttle Pod Commissioning
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_SHUTTLE_POD_COMMISSIONING.py
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 TEST_SHUTTLE_POD_COMMISSIONING.py
    ) else (
        python TEST_SHUTTLE_POD_COMMISSIONING.py
    )
)

echo.
pause
