@echo off
setlocal
title FOXAI Core v10.1 - Grounded Mission Intelligence

cd /d "%~dp0"

echo ==========================================
echo FOXAI Core v10.1
echo Grounded Mission Intelligence
echo ==========================================
echo.
echo This patches:
echo core_v10\memory_engine.py
echo.
echo A backup will be created automatically.
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_GROUNDED_MEMORY_V10_1.py
) else (
    python PATCH_GROUNDED_MEMORY_V10_1.py
)

echo.
pause
