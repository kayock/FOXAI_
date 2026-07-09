@echo off
setlocal
title FOXAI v10 Mission Intelligence Engine Patch

cd /d "%~dp0"

echo ==========================================
echo FOXAI v10 Mission Intelligence Engine
echo ==========================================
echo.
echo This patches:
echo core\foxai_web.py
echo.
echo A backup will be created automatically.
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_FOXAI_V10.py
) else (
    python PATCH_FOXAI_V10.py
)

echo.
pause
