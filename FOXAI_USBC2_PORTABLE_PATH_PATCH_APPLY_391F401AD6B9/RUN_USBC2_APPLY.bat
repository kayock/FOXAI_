@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI USB C2-A
echo Approved Portable Path Commissioning Patch Apply
echo ============================================================
echo.
echo APPROVED PLAN:
echo 391F401AD6B9
echo.
echo This operation will:
echo - back up the exact current commissioning BAT and Python source
echo - replace only those two approved files
echo - verify both replacements and the unchanged commissioning guide
echo.
echo It will NOT:
echo - change any other FOXAI file
echo - install or download packages
echo - create ComfyUI folders
echo - launch FOXAI, WebUI, Desktop, ComfyUI, browser, or models
echo - use the network
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

"%PY%" -s "%~dp0apply_usbc2_patch.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo USB C2-A patch apply completed and verified.
    echo Do not rerun commissioning yet.
    echo Upload the newest APPLY_OUTPUT\...\UPLOAD_THIS folder first.
) else (
    echo USB C2-A stopped with exit code %RC%.
    echo Upload the newest APPLY_OUTPUT\...\UPLOAD_THIS folder.
)
echo.
pause
exit /b %RC%
