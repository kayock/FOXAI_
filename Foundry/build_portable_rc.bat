@echo off
title KayocktheOS Portable Release Candidate
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundryuild_portable_rc.py
) else (
    py Foundryuild_portable_rc.py
)

echo.
pause
