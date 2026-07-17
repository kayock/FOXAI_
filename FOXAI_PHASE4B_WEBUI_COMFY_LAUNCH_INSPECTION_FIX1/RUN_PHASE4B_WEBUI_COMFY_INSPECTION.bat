@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Phase 4B
echo WebUI ComfyUI Launch Read-Only Inspection
echo ============================================================
echo.
echo This inspection will:
echo - verify the WebUI launcher and relevant source files
echo - inspect the exact ComfyUI route, command, cwd, and environment handling
echo - compare inherited-host-Python versus clean-host-Python torch imports
echo - identify whether environment inheritance is the likely failure
echo.
echo It will NOT:
echo - modify or patch any live file
echo - launch FOXAI, WebUI, ComfyUI, a browser, or a model
echo - install or download anything
echo - scan entire drives
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

"%PY%" -s "%~dp0phase4b_webui_comfy_inspection.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Phase 4B inspection completed.
) else (
    echo Phase 4B inspection stopped with exit code %RC%.
)
echo Upload the newest INSPECTION_OUTPUT\...\UPLOAD_THIS folder.
echo.
pause
exit /b %RC%
