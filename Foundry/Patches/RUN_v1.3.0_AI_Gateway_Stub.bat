@echo off
title KayocktheOS v1.3.0 AI Gateway Stub
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS v1.3.0 AI Gateway Stub
echo ==========================================
echo.
echo This patch creates a backup first.
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_v1.3.0_ai_gateway_stub.py
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py Foundry\Patches\apply_v1.3.0_ai_gateway_stub.py
    ) else (
        echo Python was not found.
        echo Cannot run patch.
    )
)

echo.
pause
