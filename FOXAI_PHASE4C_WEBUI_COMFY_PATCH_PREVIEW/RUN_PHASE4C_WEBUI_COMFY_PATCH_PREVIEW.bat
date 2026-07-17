@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Phase 4C-P
echo WebUI ComfyUI Exact Patch Preview
echo ============================================================
echo.
echo PREVIEW ONLY. No live file will be changed or launched.
echo.

set "FOXAI_ROOT="
for %%R in ("%~dp0.." "%~dp0..\.." "%~dp0") do (
    if exist "%%~fR\core\foxai_web.py" if exist "%%~fR\START_FOXAI_WEB_PORTABLE.bat" (
        set "FOXAI_ROOT=%%~fR"
        goto :ROOT_FOUND
    )
)
if exist "Z:\FOXAI\core\foxai_web.py" if exist "Z:\FOXAI\START_FOXAI_WEB_PORTABLE.bat" set "FOXAI_ROOT=Z:\FOXAI"

:ROOT_FOUND
if not defined FOXAI_ROOT (
    echo ERROR: FOXAI root was not found.
    pause
    exit /b 1
)

set "PY=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
if not exist "%PY%" set "PY=%FOXAI_ROOT%\env\python\python.exe"
if not exist "%PY%" (
    echo ERROR: No approved FOXAI Python controller was found.
    pause
    exit /b 1
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONHOME="
set "PYTHONPATH="

"%PY%" -s "%~dp0phase4c_webui_comfy_patch_preview.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
echo Phase 4C preview exited with code %RC%.
echo Upload the newest PREVIEW_OUTPUT\...\UPLOAD_THIS folder.
echo.
pause
exit /b %RC%
