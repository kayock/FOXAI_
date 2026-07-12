@echo off
title KayocktheOS v1.0.0 Portable Release Candidate
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS v1.0.0 Portable RC Toolkit
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_v1.0.0_portable_rc.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_v1.0.0_portable_rc.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
