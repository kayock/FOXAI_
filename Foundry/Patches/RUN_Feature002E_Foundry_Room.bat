@echo off
title KayocktheOS Feature 002E Foundry Room
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS Feature 002E - Foundry Room
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_feature002e_foundry_room.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_feature002e_foundry_room.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
