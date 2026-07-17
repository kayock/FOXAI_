@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Phase 4A
echo Repair and Optimization Preflight
echo ============================================================
echo.
echo READ-ONLY PREFLIGHT:
echo - verifies portable runtimes and known-good launchers
echo - inventories Repair Bay and offline wheelhouse readiness
echo - profiles this machine and optional host tools
echo - labels dependencies as USB, HOST PC, or NOT_FOUND
echo - produces READY, READY_WITH_NOTES, or NEEDS_ATTENTION
echo.
echo It will NOT repair, install, download, delete, overwrite,
echo launch FOXAI, launch ComfyUI, or scan entire drives.
echo.

set "FOXAI_ROOT="
for %%R in ("%~dp0.." "%~dp0..\.." "%~dp0") do (
    if exist "%%~fR\foxai.py" if exist "%%~fR\Runtime\Desktop\python\python.exe" (
        set "FOXAI_ROOT=%%~fR"
        goto :ROOT_FOUND
    )
)

if exist "Z:\FOXAI\foxai.py" if exist "Z:\FOXAI\Runtime\Desktop\python\python.exe" (
    set "FOXAI_ROOT=Z:\FOXAI"
)

:ROOT_FOUND
if not defined FOXAI_ROOT (
    echo ERROR: FOXAI root was not found.
    echo Extract this complete folder inside the FOXAI folder.
    echo Nothing was changed.
    pause
    exit /b 1
)

set "PY=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
if not exist "%PY%" set "PY=%FOXAI_ROOT%\env\python\python.exe"

if not exist "%PY%" (
    echo ERROR: No approved FOXAI Python controller was found.
    echo Nothing was changed.
    pause
    exit /b 1
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONHOME="
set "PYTHONPATH="

echo FOXAI root: %FOXAI_ROOT%
echo Controller: %PY%
echo.

"%PY%" -s "%~dp0repair_optimization_preflight.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
echo Preflight finished with exit code %RC%.
echo Upload the newest PREFLIGHT_OUTPUT\...\UPLOAD_THIS folder.
echo.
pause
exit /b %RC%
