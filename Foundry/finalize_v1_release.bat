@echo off
title KayocktheOS v1.0.0 Release Finalizer
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundryinalize_v1_release.py
) else (
    py Foundryinalize_v1_release.py
)

echo.
pause
