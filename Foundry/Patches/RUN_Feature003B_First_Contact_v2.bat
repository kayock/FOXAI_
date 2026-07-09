@echo off
title KayocktheOS Feature 003B First Contact v2
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS Feature 003B - First Contact v2
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_feature003b_first_contact_v2.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_feature003b_first_contact_v2.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
