@echo off
setlocal EnableExtensions
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "ACTIVATOR=%FOXAI_ROOT%\System\PortableRuntime\launch_comfyui_isolated.py"
set "TARGET=%FOXAI_ROOT%\Runtime\ComfyUI\site-packages"
set "MAIN=%FOXAI_ROOT%\ComfyUI\main.py"

if not exist "%PYTHON%" echo ERROR: Portable Python missing.& pause & exit /b 2
if not exist "%ACTIVATOR%" echo ERROR: Isolated activator missing.& pause & exit /b 3
if not exist "%TARGET%\torch\__init__.py" echo ERROR: Isolated target incomplete.& pause & exit /b 4
if not exist "%MAIN%" echo ERROR: ComfyUI main.py missing.& pause & exit /b 5

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -I -B -S "%ACTIVATOR%" --root "%FOXAI_ROOT%" -- --cpu
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo ComfyUI exited normally.) else echo ComfyUI exited with code %RC%.
pause
exit /b %RC%
