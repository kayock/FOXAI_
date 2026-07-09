@echo off
title KayocktheOS Package Release
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\package_release.py
) else (
    py Foundry\package_release.py
)
pause
