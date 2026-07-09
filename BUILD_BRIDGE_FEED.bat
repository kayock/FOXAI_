@echo off
setlocal
title FOXAI Operation Bridge Alive v8.0 Bridge Feed

cd /d "%~dp0"

echo ==========================================
echo FOXAI Operation Bridge Alive v8.0
echo Bridge Feed Builder
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" BUILD_BRIDGE_FEED.py
) else (
    python BUILD_BRIDGE_FEED.py
)

echo.
pause
