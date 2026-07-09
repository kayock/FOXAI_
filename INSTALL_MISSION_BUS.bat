@echo off
setlocal
title Install FOXAI Mission Bus Phase 2

cd /d "%~dp0"

echo ==========================================
echo Installing FOXAI Mission Bus Phase 2
echo ==========================================
echo.

if not exist "core_v10" (
    echo [ERROR] core_v10 folder not found.
    echo Extract this ZIP directly into your FOXAI root.
    pause
    exit /b 1
)

echo Files are already in place if this ZIP was extracted into FOXAI root.
echo.
echo Run TEST_MISSION_BUS.bat to verify.
echo.
pause
