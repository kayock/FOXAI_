@echo off
title KayocktheOS Feature 007 Academy Bridge
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS Feature 007 - Academy Bridge
echo ==========================================
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_feature007_academy_bridge.py
) else (
    py Foundry\Patches\apply_feature007_academy_bridge.py
)

echo.
pause
