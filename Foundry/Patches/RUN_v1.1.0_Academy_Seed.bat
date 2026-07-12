@echo off
title KayocktheOS v1.1.0 Academy Seed
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS v1.1.0 Academy Seed
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_v1.1.0_academy_seed.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_v1.1.0_academy_seed.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
