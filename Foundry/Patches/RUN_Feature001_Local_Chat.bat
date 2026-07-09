@echo off
title KayocktheOS Feature 001 Local Chat
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS Feature 001 - Local Chat
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_feature001_local_chat.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_feature001_local_chat.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
