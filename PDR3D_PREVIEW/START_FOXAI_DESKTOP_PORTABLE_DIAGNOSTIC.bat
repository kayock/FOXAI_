@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "ROOT=%~dp0"
set "PYTHONNOUSERSITE=1"
set "PYTHONHOME=%ROOT%Runtime\Desktop\python"
set "PYTHONPATH=%ROOT%Runtime\Desktop\site-packages;%ROOT%Runtime\Core\site-packages;%ROOT%"

echo ============================================================
echo FOXAI Portable Desktop Runtime Diagnostic
echo ============================================================
echo.
echo This verifies the new USB-owned runtime.
echo It does not launch FOXAI or ComfyUI.
echo.

"%ROOT%Runtime\Desktop\python\python.exe" -s "%ROOT%System\PortableRuntime\verify_desktop_runtime.py" --root "%ROOT%."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Desktop runtime diagnostic PASSED.
) else (
    echo Desktop runtime diagnostic FAILED with exit code %RC%.
)
echo.
pause
exit /b %RC%
