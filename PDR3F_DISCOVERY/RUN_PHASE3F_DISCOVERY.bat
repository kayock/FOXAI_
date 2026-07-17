@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3F
echo Combined Startup Read-Only Discovery
echo ============================================================
echo.
echo This package will inspect the existing working shortcut and
echo launcher chain so the proven ComfyUI startup can be preserved.
echo.
echo It will NOT:
echo - modify any FOXAI file or shortcut
echo - launch FOXAI, ComfyUI, or a browser
echo - install or download anything
echo - scan entire drives
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

"%PY%" -s "%~dp0phase3f_discovery.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Phase 3F discovery completed and verified.
) else (
    echo Phase 3F discovery stopped with exit code %RC%.
)
echo Upload the newest DISCOVERY_OUTPUT\...\UPLOAD_THIS folder.
echo.
pause
exit /b %RC%
