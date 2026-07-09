@echo off
title KayocktheOS Feature 004D Model Profiles
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS Feature 004D - Model Profiles
echo ==========================================
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_feature004d_model_profiles.py
) else (
    py Foundry\Patches\apply_feature004d_model_profiles.py
)

echo.
pause
