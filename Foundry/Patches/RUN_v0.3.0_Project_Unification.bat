@echo off
title KayocktheOS v0.3.0 Project Unification
color 0A

cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS v0.3.0 Project Unification
echo ==========================================
echo.
echo This will create a backup before changing files.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_v0.3.0_project_unification.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_v0.3.0_project_unification.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
