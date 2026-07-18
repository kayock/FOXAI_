@echo off
setlocal EnableExtensions
cd /d "%~dp0"
for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
for %%I in ("%~dp0.") do set "PACKAGE_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_ROOT%\System\Integration\usbc3g_apply.py"

title FOXAI USB C3G - Controlled No-Launch Integration

echo ================================================================
echo  FOXAI USB C3G - CONTROLLED NO-LAUNCH INTEGRATION
echo ================================================================
echo.
echo This stage applies only the exact C3F-reviewed integration files.
echo It will NOT launch FOXAI, WebUI, Desktop, or ComfyUI.
echo It will NOT access the network or modify the isolated package target.
echo.

if not exist "%PYTHON%" (
    echo [STOPPED] Portable Python is missing.
    pause
    exit /b 2
)
if not exist "%SCRIPT%" (
    echo [STOPPED] C3G apply script is missing.
    pause
    exit /b 3
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --package-root "%PACKAGE_ROOT%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [COMPLETE] C3G finished successfully. ComfyUI was not launched.
) else (
    echo [STOPPED] C3G exited with code %RC%. ComfyUI was not launched.
)
echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%
