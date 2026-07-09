@echo off
title KayocktheOS v0.7.0 Service Bus
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS v0.7.0 Service Bus
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_v0.7.0_service_bus.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_v0.7.0_service_bus.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
