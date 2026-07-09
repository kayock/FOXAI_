@echo off
title KayocktheOS First Contact Diagnostics
color 0A
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundryirst_contact_diagnostics.py
) else (
    py Foundryirst_contact_diagnostics.py
)

echo.
echo Report:
echo Foundry\Reports\FIRST_CONTACT_DIAGNOSTICS.md
echo.
pause
