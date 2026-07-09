@echo off
setlocal
title FOXAI v9.2 Mission Intelligence + Novel Forge Patch

cd /d "%~dp0"

echo ==========================================
echo FOXAI v9.2 Patch
echo Mission Intelligence + Professor Novel Forge
echo ==========================================
echo.
echo This will patch:
echo core\foxai_web.py
echo.
echo A backup will be created automatically.
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_FOXAI_V9_2.py
) else (
    python PATCH_FOXAI_V9_2.py
)

echo.
pause
