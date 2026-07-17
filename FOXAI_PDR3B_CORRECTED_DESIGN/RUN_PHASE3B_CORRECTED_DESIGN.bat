@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3B - Corrected Design
echo ============================================================
echo.
echo READ-ONLY DESIGN PROBE:
echo - checks the two exact USB-root shortcuts only
echo - reads the existing launch chain and imported FOXAI files
echo - probes Python runtimes with short timeouts
echo - does not scan drives
echo - does not launch FOXAI or ComfyUI
echo - does not install or download anything
echo - does not modify shortcuts, launchers, runtimes, or live files
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

echo FOXAI root: %FOXAI_ROOT%
echo Runtime:    %PY%
echo.

"%PY%" "%~dp0phase3b_corrected_design.py" --root "%FOXAI_ROOT%" --bundle "%~dp0"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Phase 3B corrected design completed.
    echo Zip the newest folder under design_output and upload it.
) else (
    echo Phase 3B stopped with exit code %RC%.
    echo Review the newest receipt under design_output.
)
echo.
pause
exit /b %RC%
