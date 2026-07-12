@echo off
title KayocktheOS Feature 006 Core Working
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS Feature 006 - Core Working
echo ==========================================
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_feature006_core_working.py
) else (
    py Foundry\Patches\apply_feature006_core_working.py
)

echo.
pause
