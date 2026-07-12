@echo off
title KayocktheOS v0.4.0 Living System Scanner
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS v0.4.0 Living System Scanner
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_v0.4.0_living_system_scanner.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_v0.4.0_living_system_scanner.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
