@echo off
setlocal
title FOXAI CM v2.1 Extension Manifest Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v2.1 Extension Manifest Test
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_EXTENSION_MANIFESTS.py
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 TEST_EXTENSION_MANIFESTS.py
    ) else (
        python TEST_EXTENSION_MANIFESTS.py
    )
)

echo.
pause
