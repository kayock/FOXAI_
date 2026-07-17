@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3D-P
echo Preview-First Exact Live Apply Plan
echo ============================================================
echo.
echo PREVIEW ONLY:
echo - verifies the completed Phase 3C quarantine
echo - hashes the exact quarantined source files
echo - checks only exact proposed destination paths
echo - generates an exact add-only plan and approval code
echo - does not copy anything into live FOXAI
echo - does not launch FOXAI, ComfyUI, or a browser
echo - does not change shortcuts or existing launchers
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

"%PY%" "%~dp0phase3d_preview.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Phase 3D preview verified.
    echo Upload only the newest PREVIEW_OUTPUT\...\UPLOAD_THIS folder.
) else (
    echo Phase 3D preview stopped with exit code %RC%.
    echo Upload only the newest PREVIEW_OUTPUT\...\UPLOAD_THIS folder.
)
echo.
pause
exit /b %RC%
