@echo off
setlocal
title FOXAI Capability Bus Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI Capability Bus Test
echo ==========================================
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 TEST_CAPABILITY_BUS.py
) else (
    python TEST_CAPABILITY_BUS.py
)

echo.
pause
