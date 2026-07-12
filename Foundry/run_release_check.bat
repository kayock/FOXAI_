@echo off
title KayocktheOS Release Check
cd /d "%~dp0.."
where python >nul 2>nul
if %errorlevel%==0 (
    python Foundryelease_check.py
) else (
    py Foundryelease_check.py
)
pause
