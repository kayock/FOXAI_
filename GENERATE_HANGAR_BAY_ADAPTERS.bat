@echo off
setlocal
title FOXAI Hangar Bay Adapter Generator

cd /d "%~dp0"

echo ==========================================
echo FOXAI Hangar Bay Adapter Generator
echo ==========================================
echo.
echo This scans:
echo %~d0\Hanger Bay
echo.
echo And creates:
echo %CD%\Capabilities\hangar_*\adapter.json
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 GENERATE_HANGAR_BAY_ADAPTERS.py
) else (
    python GENERATE_HANGAR_BAY_ADAPTERS.py
)

echo.
pause
