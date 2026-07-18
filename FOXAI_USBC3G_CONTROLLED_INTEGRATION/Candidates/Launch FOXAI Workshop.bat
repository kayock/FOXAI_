@echo off
title Launch FOXAI Workshop
cd /d "%~dp0"

echo ========================================
echo Launching ComfyUI CPU backend...
echo ========================================
if exist "%~dp0ComfyUI\main.py" (
    start "ComfyUI CPU" cmd /k ""%~dp0Runtime\Desktop\python\python.exe" -I -B -S "%~dp0System\PortableRuntime\launch_comfyui_isolated.py" --root "%~dp0." -- --cpu"
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
