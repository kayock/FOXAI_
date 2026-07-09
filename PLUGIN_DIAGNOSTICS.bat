@echo off
setlocal
title FOXAI Plugin Diagnostics

cd /d "%~dp0"

echo ==========================================
echo FOXAI Plugin Diagnostics
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" PLUGIN_DIAGNOSTICS.py %*
) else (
    python PLUGIN_DIAGNOSTICS.py %*
)

echo.
pause
