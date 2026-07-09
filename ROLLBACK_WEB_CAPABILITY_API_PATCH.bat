@echo off
setlocal
title FOXAI Rollback Web Capability API Patch

cd /d "%~dp0"

echo ==========================================
echo FOXAI Rollback Web Capability API Patch
echo ==========================================
echo.
echo This restores the latest foxai_web backup.
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 ROLLBACK_WEB_CAPABILITY_API_PATCH.py
) else (
    python ROLLBACK_WEB_CAPABILITY_API_PATCH.py
)

echo.
pause
