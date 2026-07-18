@echo off
setlocal EnableExtensions
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "FOXAI_ROOT=%%~fI"

set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "PYTHONW=%FOXAI_ROOT%\Runtime\Desktop\python\pythonw.exe"
set "QUIET_START=%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py"
set "FOXAI_APP=%FOXAI_ROOT%\foxai.py"

title FOXAI Desktop Launcher

echo ============================================================
echo FOXAI DESKTOP
echo ============================================================
echo Starting ComfyUI quietly and opening FOXAI Desktop.
echo.

if not exist "%PYTHON%" (
    echo ERROR: Portable Python was not found:
    echo %PYTHON%
    pause
    exit /b 2
)
if not exist "%QUIET_START%" (
    echo ERROR: Quiet ComfyUI starter was not found:
    echo %QUIET_START%
    pause
    exit /b 3
)
if not exist "%FOXAI_APP%" (
    echo ERROR: FOXAI Desktop was not found:
    echo %FOXAI_APP%
    pause
    exit /b 4
)

set "PYTHONHOME=%FOXAI_ROOT%\Runtime\Desktop\python"
set "PYTHONPATH=%FOXAI_ROOT%\Runtime\Desktop\site-packages;%FOXAI_ROOT%\Runtime\Core\site-packages;%FOXAI_ROOT%"
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"

"%PYTHON%" -I -B -S "%QUIET_START%" --root "%FOXAI_ROOT%" --source desktop
if errorlevel 1 (
    echo.
    echo ERROR: ComfyUI quiet startup failed.
    echo FOXAI Desktop was not started.
    pause
    exit /b 5
)

echo Opening FOXAI Desktop...
if exist "%PYTHONW%" (
    start "" "%PYTHONW%" -s "%FOXAI_APP%"
) else (
    start "FOXAI Desktop" "%ComSpec%" /d /k ^
      ""%PYTHON%" -s "%FOXAI_APP%""
)

timeout /t 2 /nobreak >nul
exit /b 0
