@echo off
setlocal
title FOXAI Core v10 Phase 2 Mission Bus Test
cd /d "%~dp0"

echo ==========================================
echo FOXAI Core v10 Phase 2 - Mission Bus Test
echo ==========================================
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 TEST_MISSION_BUS.py
) else (
    python TEST_MISSION_BUS.py
)

echo.
pause
