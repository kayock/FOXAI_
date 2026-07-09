@echo off
title KayocktheOS Feature 005 AnythingLLM Adapter
color 0A
cd /d "%~dp0..\.."

echo ==========================================
echo KayocktheOS Feature 005 - AnythingLLM Adapter
echo ==========================================
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\Patches\apply_feature005_anythingllm_adapter.py
) else (
    py Foundry\Patches\apply_feature005_anythingllm_adapter.py
)

echo.
pause
