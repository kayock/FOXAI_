@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3F-P
echo Combined Portable Workshop Launcher Preview
echo ============================================================
echo.
echo PREVIEW ONLY:
echo - verifies the read-only discovery evidence
echo - verifies the working launcher chain and protected state
echo - checks the host python command used by working ComfyUI
echo - proposes one separate combined launcher
echo - does not add, modify, or launch anything
echo - does not change either shortcut
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

"%PY%" -s "%~dp0phase3f_combined_preview.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Phase 3F combined-launcher preview verified.
    echo Upload the newest PREVIEW_OUTPUT\...\UPLOAD_THIS folder.
) else (
    echo Phase 3F preview stopped with exit code %RC%.
    echo Upload the newest PREVIEW_OUTPUT\...\UPLOAD_THIS folder.
)
echo.
pause
exit /b %RC%
