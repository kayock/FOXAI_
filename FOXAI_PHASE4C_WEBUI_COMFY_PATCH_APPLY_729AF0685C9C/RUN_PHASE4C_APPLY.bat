@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Phase 4C-A
echo Approved WebUI ComfyUI Patch Apply
echo ============================================================
echo.
echo APPROVED PLAN:
echo 729AF0685C9C
echo.
echo This operation will:
echo - back up the exact current core\foxai_web.py
echo - replace only core\foxai_web.py with the approved version
echo - verify the replacement and all protected hashes
echo.
echo It will NOT:
echo - change any launcher or shortcut
echo - change ComfyUI source
echo - launch FOXAI, WebUI, ComfyUI, a browser, or a model
echo - install or download anything
echo - use the network
echo.

set "FOXAI_ROOT="
for %%R in ("%~dp0.." "%~dp0..\.." "%~dp0") do (
    if exist "%%~fR\core\foxai_web.py" if exist "%%~fR\START_FOXAI_WEB_PORTABLE.bat" (
        set "FOXAI_ROOT=%%~fR"
        goto :ROOT_FOUND
    )
)

if exist "Z:\FOXAI\core\foxai_web.py" if exist "Z:\FOXAI\START_FOXAI_WEB_PORTABLE.bat" (
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

"%PY%" -s "%~dp0phase4c_apply.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Phase 4C-A patch apply completed and verified.
    echo Do not test the WebUI button yet.
    echo Upload the newest APPLY_OUTPUT\...\UPLOAD_THIS folder first.
) else (
    echo Phase 4C-A stopped with exit code %RC%.
    echo Upload the newest APPLY_OUTPUT\...\UPLOAD_THIS folder.
)
echo.
pause
exit /b %RC%
