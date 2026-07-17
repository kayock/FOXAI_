@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3E-P
echo Separate Portable Launcher Preview
echo ============================================================
echo.
echo PREVIEW ONLY:
echo - verifies the passed live USB runtime diagnostic
echo - verifies protected FOXAI files and shortcuts
echo - checks the exact new launcher destination
echo - generates the launcher, plan ID, and approval phrase
echo - does not add or launch anything
echo - does not modify shortcuts or existing launchers
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

"%PY%" -s "%~dp0phase3e_launcher_preview.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Phase 3E launcher preview verified.
    echo Upload the newest PREVIEW_OUTPUT\...\UPLOAD_THIS folder.
) else (
    echo Phase 3E preview stopped with exit code %RC%.
    echo Upload the newest PREVIEW_OUTPUT\...\UPLOAD_THIS folder.
)
echo.
pause
exit /b %RC%
