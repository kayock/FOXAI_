@echo off
setlocal
title FOXAI Builder - Operation Bridge Alive v8.1

cd /d "%~dp0"

echo ==========================================
echo FOXAI Builder - Operation Bridge Alive v8.1
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" BUILD_FOXAI.py
) else (
    python BUILD_FOXAI.py
)

echo.
pause
