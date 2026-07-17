@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3F-A
echo Approved Combined Workshop Launcher Apply
echo ============================================================
echo.
echo APPROVED PLAN:
echo 9418899AB4F8
echo.
echo This operation will add one new launcher:
echo START_FOXAI_WORKSHOP_PORTABLE.bat
echo.
echo It will NOT:
echo - overwrite or modify any existing file
echo - change either USB-root shortcut
echo - change existing launchers or FOXAI source
echo - launch FOXAI, ComfyUI, or a browser
echo - install or download packages
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
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONPATH="
set "PYTHONHOME="

echo FOXAI root: %FOXAI_ROOT%
echo Controller: %PY%
echo.

"%PY%" -s "%~dp0phase3f_apply.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Phase 3F-A launcher apply completed and verified.
    echo Do not run the new combined launcher yet.
    echo Upload the newest APPLY_OUTPUT\...\UPLOAD_THIS folder first.
) else (
    echo Phase 3F-A stopped with exit code %RC%.
    echo Upload the newest APPLY_OUTPUT\...\UPLOAD_THIS folder.
)
echo.
pause
exit /b %RC%
