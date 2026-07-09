@echo off
setlocal
title FOXAI Capability Manager v1 Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI Capability Manager v1 Test
echo ==========================================
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 TEST_CAPABILITY_MANAGER.py
) else (
    python TEST_CAPABILITY_MANAGER.py
)

echo.
pause
