@echo off
setlocal
title FOXAI Core v10.3 - Remembered-Only Recall Route

cd /d "%~dp0"

echo ==========================================
echo FOXAI Core v10.3
echo Remembered-Only Recall Route
echo ==========================================
echo.
echo This patches:
echo core_v10\mission_engine.py
echo.
echo A backup will be created automatically.
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_REMEMBERED_ONLY_ROUTE_V10_3.py
) else (
    python PATCH_REMEMBERED_ONLY_ROUTE_V10_3.py
)

echo.
pause
