@echo off
setlocal
title FOXAI Orion v9.1 Purple Desktop Shell

cd /d "%~dp0"

echo ==========================================
echo FOXAI Orion v9.1 Purple Desktop Shell
echo ==========================================
echo.
echo This will backup and patch the existing CustomTkinter UI.
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" APPLY_PURPLE_DESKTOP.py
) else (
    python APPLY_PURPLE_DESKTOP.py
)

echo.
pause
