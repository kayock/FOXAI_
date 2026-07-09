@echo off
title Launch FOXAI Workshop
cd /d "%~dp0"

echo ========================================
echo Launching ComfyUI CPU backend...
echo ========================================
if exist "%~dp0ComfyUI\main.py" (
    start "ComfyUI CPU" cmd /k "cd /d "%~dp0ComfyUI" && python main.py --cpu"
) else (
    echo ComfyUI folder not found at %~dp0ComfyUI
)

echo.
echo Waiting 8 seconds before starting FOXAI...
timeout /t 8 /nobreak >nul

echo ========================================
echo Launching FOXAI...
echo ========================================
start "FOXAI" cmd /k "cd /d "%~dp0" && python foxai.py"
