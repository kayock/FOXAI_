@echo off
setlocal
title FOXAI Extension Manager v1 Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI Extension Manager v1 Test
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_EXTENSION_MANAGER.py
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 TEST_EXTENSION_MANAGER.py
    ) else (
        python TEST_EXTENSION_MANAGER.py
    )
)

echo.
pause
