@echo off
setlocal EnableExtensions
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "MANAGER=%FOXAI_ROOT%\System\PortableRuntime\manage_comfyui_normal.py"
if not exist "%PYTHON%" echo ERROR: Portable Python is missing.& pause & exit /b 2
if not exist "%MANAGER%" echo ERROR: ComfyUI normal controller is missing.& pause & exit /b 3
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -I -B -S "%MANAGER%" --root "%FOXAI_ROOT%" stop
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
