@echo off
title KayocktheOS v1.4.0 Local Runtime Connector
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS v1.4.0 Local Runtime Connector
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_v1.4.0_local_runtime_connector.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_v1.4.0_local_runtime_connector.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
