@echo off
title KayocktheOS Feature 004B Kobold Panel
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS Feature 004B - Kobold Panel
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_feature004b_kobold_panel.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_feature004b_kobold_panel.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
