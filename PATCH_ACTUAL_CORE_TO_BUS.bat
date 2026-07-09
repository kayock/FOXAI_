@echo off
setlocal
title FOXAI Actual Core Bus Wiring Patch

cd /d "%~dp0"

echo ==========================================
echo FOXAI Actual Core Bus Wiring Patch
echo ==========================================
echo.
echo This patch is targeted to your uploaded core\foxai_web.py.
echo It requires core_v10\mission_bus.py to already exist.
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_ACTUAL_CORE_TO_BUS.py
) else (
    python PATCH_ACTUAL_CORE_TO_BUS.py
)

echo.
pause
