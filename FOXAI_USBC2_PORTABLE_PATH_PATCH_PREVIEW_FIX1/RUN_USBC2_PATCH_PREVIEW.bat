@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI USB C2
echo Portable Path Exact Patch Preview
echo ============================================================
echo.
echo PREVIEW ONLY:
echo - verifies the exact live commissioning files
echo - verifies the captured portable module proof
echo - verifies the proposed two-file patch and exact diff
echo - produces an approval phrase
echo.
echo It will NOT modify FOXAI, install packages, create folders,
echo launch services, or apply the patch.
echo.

set "FOXAI_ROOT="
for %%R in ("%~dp0.." "%~dp0..\.." "%~dp0") do (
    if exist "%%~fR\COMMISSION_FOXAI_USB.bat" if exist "%%~fR\System\Commissioning\commission_usb.py" (
        set "FOXAI_ROOT=%%~fR"
        goto :ROOT_FOUND
    )
)

:ROOT_FOUND
if not defined FOXAI_ROOT (
    echo ERROR: FOXAI root was not found.
    echo Extract this complete folder inside the FOXAI repository.
    echo Nothing was changed.
    pause
    exit /b 1
)

set "PY=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
if not exist "%PY%" (
    echo ERROR: Portable Desktop Python was not found:
    echo %PY%
    echo Nothing was changed.
    pause
    exit /b 1
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONHOME="
set "PYTHONPATH=%FOXAI_ROOT%\Runtime\Desktop\site-packages;%FOXAI_ROOT%\Runtime\Core\site-packages"

echo FOXAI root: %FOXAI_ROOT%
echo Controller: %PY%
echo.

"%PY%" -s "%~dp0verify_usbc2_patch_preview.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo USB C2 patch preview completed and verified.
) else (
    echo USB C2 patch preview stopped with exit code %RC%.
)
echo Upload the newest PREVIEW_OUTPUT\...\UPLOAD_THIS folder.
echo.
pause
exit /b %RC%
