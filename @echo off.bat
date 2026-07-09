@echo off
cd /d "%~dp0"
title FoxAI Launcher

:menu
cls
echo ==========================
echo          FOX AI
echo ==========================
echo.
echo 1) Smart Chat - Q8
echo 2) Fast Chat - Q4
echo 3) Exit
echo.
set /p choice=Choose: 

if "%choice%"=="1" goto smart
if "%choice%"=="2" goto fast
if "%choice%"=="3" exit
goto menu

:smart
cls
echo Starting FoxAI Smart Mode...
Engine\llama-server.exe ^
  --model "Models\Chat\Qwen3-8B-Q8_0.gguf" ^
  --host 127.0.0.1 ^
  --port 8080 ^
  --ctx-size 8192 ^
  --threads 12
pause
goto menu

:fast
cls
echo Starting FoxAI Fast Mode...
Engine\llama-server.exe ^
  --model "Models\Chat\Qwen3-8B-Q4_K_M.gguf" ^
  --host 127.0.0.1 ^
  --port 8080 ^
  --ctx-size 8192 ^
  --threads 12
pause
goto menu