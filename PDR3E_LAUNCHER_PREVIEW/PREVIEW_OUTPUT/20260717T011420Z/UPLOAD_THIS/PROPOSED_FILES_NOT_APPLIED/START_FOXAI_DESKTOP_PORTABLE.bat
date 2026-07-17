@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "ROOT=%~dp0"
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONHOME=%ROOT%Runtime\Desktop\python"
set "PYTHONPATH=%ROOT%Runtime\Desktop\site-packages;%ROOT%Runtime\Core\site-packages;%ROOT%"

echo ============================================================
echo FOXAI Portable Desktop
echo ============================================================
echo Runtime: %ROOT%Runtime\Desktop\python\python.exe
echo.

"%ROOT%Runtime\Desktop\python\python.exe" -s "%ROOT%System\PortableRuntime\verify_desktop_runtime.py" --root "%ROOT%."
if errorlevel 1 (
    echo.
    echo Portable Desktop runtime verification failed.
    echo FOXAI was not launched.
    pause
    exit /b 2
)

echo.
echo Portable runtime verified. Launching FOXAI...
"%ROOT%Runtime\Desktop\python\python.exe" -s "%ROOT%foxai.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo FOXAI exited with code %RC%.
    pause
)
exit /b %RC%
