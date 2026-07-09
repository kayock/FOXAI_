@echo off
title KayocktheOS
color 0A
set KAYOCK_ROOT=%~dp0
cd /d "%KAYOCK_ROOT%"

echo Starting KayocktheOS...
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python System\Launchers\launch.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py System\Launchers\launch.py
    ) else (
        echo Python was not found.
        pause
    )
)
