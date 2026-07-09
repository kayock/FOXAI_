@echo off
setlocal
title FOXAI Hangar Bay Package Inventory

cd /d "%~dp0"

echo ==========================================
echo FOXAI Hangar Bay Package Inventory
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" HANGAR_BAY_INVENTORY.py
) else (
    python HANGAR_BAY_INVENTORY.py
)

echo.
pause
