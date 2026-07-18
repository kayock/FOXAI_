@echo off
setlocal EnableExtensions
title Launch FOXAI Workshop
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "MANAGER=%FOXAI_ROOT%\System\PortableRuntime\manage_comfyui_normal.py"

echo ========================================
echo Starting verified ComfyUI Safe Normal CPU...
echo ========================================
"%PYTHON%" -I -B -S "%MANAGER%" --root "%FOXAI_ROOT%" spawn --source workshop
if errorlevel 1 (
  echo ERROR: ComfyUI did not reach verified healthy state.
  echo FOXAI was not started.
  pause
  exit /b 5
)

echo.
echo ========================================
echo Launching FOXAI...
echo ========================================
start "FOXAI" cmd /k "cd /d "%FOXAI_ROOT%" && python foxai.py"
exit /b 0
