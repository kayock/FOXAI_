@echo off
title KayocktheOS Core Working Launcher
color 0A
cd /d "Z:\KayocktheOS"

echo ==========================================
echo KayocktheOS Core Working Launcher
echo ==========================================
echo.
echo This is the clean startup path.
echo It does NOT call llama-batched-bench.exe.
echo.
echo 1. Start AnythingLLM
echo 2. Start KoboldCpp runtime
echo 3. Start ComfyUI / FOXAI
echo 4. Show status
echo 5. Exit
echo.
set /p choice=Choose option: 

if "%choice%"=="1" goto anything
if "%choice%"=="2" goto kobold
if "%choice%"=="3" goto comfy
if "%choice%"=="4" goto status
goto end

:anything
echo.
start "" "Z:\Apps\New folder\AnythingLLM\AnythingLLM.exe"
pause
goto end

:kobold
echo KoboldCpp not found. Put koboldcpp.exe in Z:\KayocktheOS\Engine\KoboldCpp\.
pause
goto end

:comfy
echo ComfyUI main.py found at Z:\FOXAI\ComfyUI\main.py. Use your existing FOXAI ComfyUI launcher.
pause
goto end

:status
python AI\core_working.py
pause
goto end

:end
exit /b
