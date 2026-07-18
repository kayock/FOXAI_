@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI USB C3
echo Creative Studio / ComfyUI Portability Preflight
echo ============================================================
echo.
echo READ-ONLY PREFLIGHT:
echo - inspects ComfyUI folders, launchers, Python runtimes, and torch
echo - measures USB space and relevant package/model footprints
echo - captures exact ComfyUI-related source snapshots
echo.
echo It will NOT install, download, repair, create missing folders,
echo modify FOXAI, launch ComfyUI, or use the network.
echo.

set "FOXAI_ROOT="
for %%R in ("%~dp0.." "%~dp0..\.." "%~dp0") do (
    if exist "%%~fR\COMMISSION_FOXAI_USB.bat" if exist "%%~fR\System\Commissioning\commission_usb.py" (
        set "FOXAI_ROOT=%%~fR"
        goto :ROOT_FOUND
    )
)

:ROOT_FOUND
if not defined FOXAI_ROOT (
    echo ERROR: FOXAI root was not found.
    echo Extract this complete folder inside the FOXAI repository.
    echo Nothing was changed.
    pause
    exit /b 1
)

set "PY=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
if not exist "%PY%" (
    echo ERROR: Portable Desktop Python was not found:
    echo %PY%
    echo Nothing was changed.
    pause
    exit /b 1
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONHOME="
set "PYTHONPATH=%FOXAI_ROOT%\Runtime\Desktop\site-packages;%FOXAI_ROOT%\Runtime\Core\site-packages"

echo FOXAI root: %FOXAI_ROOT%
echo Controller: %PY%
echo.

"%PY%" -s "%~dp0run_usbc3_preflight.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo USB C3 preflight completed.
) else (
    echo USB C3 preflight stopped with exit code %RC%.
)
echo Upload the newest PREFLIGHT_OUTPUT\...\UPLOAD_THIS folder.
echo.
pause
exit /b %RC%
