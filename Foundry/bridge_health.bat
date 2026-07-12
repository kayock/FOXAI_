@echo off
title KayocktheOS Bridge Health
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundryridge_health.py
) else (
    py Foundryridge_health.py
)

echo.
pause
