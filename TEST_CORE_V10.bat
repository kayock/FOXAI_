@echo off
setlocal
title FOXAI Core v10 Smoke Test
cd /d "%~dp0"

echo ==========================================
echo FOXAI Core v10 Smoke Test
echo ==========================================
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 TEST_CORE_V10.py
) else (
    python TEST_CORE_V10.py
)

echo.
pause
