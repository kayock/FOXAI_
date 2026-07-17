@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3C
echo Quarantined Runtime Acquisition and Verification
echo ============================================================
echo.
echo This phase:
echo - copies only from known Python/package folders
echo - writes only inside this bundle's Q folder
echo - does not scan drives
echo - does not launch FOXAI, ComfyUI, or a browser
echo - does not install or download packages
echo - does not change live shortcuts, launchers, runtimes, or source
echo.
echo A full Python runtime copy can take several minutes on USB.
echo Progress will be displayed.
echo.

set "FOXAI_ROOT="
for %%R in ("%~dp0.." "%~dp0..\.." "%~dp0") do (
    if exist "%%~fR\env\python\python.exe" if exist "%%~fR\foxai.py" (
        set "FOXAI_ROOT=%%~fR"
        goto :ROOT_FOUND
    )
)

if exist "Z:\FOXAI\env\python\python.exe" if exist "Z:\FOXAI\foxai.py" (
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

set "PY=%FOXAI_ROOT%\env\python\python.exe"
set "PYTHONNOUSERSITE=1"
set "PYTHONPATH="
set "PYTHONHOME="

echo FOXAI root: %FOXAI_ROOT%
echo Controller: %PY%
echo.

"%PY%" "%~dp0phase3c_quarantine.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Phase 3C quarantine acquisition verified.
    echo Upload only the small UPLOAD_THIS folder from the newest Q run.
) else (
    echo Phase 3C stopped fail-closed with exit code %RC%.
    echo Upload only the small UPLOAD_THIS folder from the newest Q run.
)
echo.
pause
exit /b %RC%
