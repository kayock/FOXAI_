@echo off
setlocal
title FOXAI CM v4.1 Bridge Officer Framework Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v4.1 Bridge Officer Test
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_BRIDGE_OFFICERS.py
) else (
    python TEST_BRIDGE_OFFICERS.py
)

echo.
pause
