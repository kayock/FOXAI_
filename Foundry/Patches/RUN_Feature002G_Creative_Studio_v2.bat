@echo off
title KayocktheOS Feature 002G v2 Creative Studio
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS Feature 002G v2 - Creative Studio
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_feature002g_creative_studio_v2.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_feature002g_creative_studio_v2.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
