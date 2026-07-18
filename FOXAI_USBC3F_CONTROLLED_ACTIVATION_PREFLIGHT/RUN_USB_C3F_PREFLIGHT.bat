@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI USB C3F - No-Launch Activation Preflight

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PORTABLE_PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "C3F_SCRIPT=%~dp0System\Activation\usbc3f_activation_review.py"

echo ============================================================
echo   FOXAI USB C3F - CONTROLLED ACTIVATION PREFLIGHT
echo ============================================================
echo.
echo This stage does NOT edit launchers and does NOT launch ComfyUI.
echo It re-verifies C3E, tests isolated activation, inventories all
echo launch surfaces, and prepares a proposed C3G change set only.
echo.

if not exist "%PORTABLE_PYTHON%" (
    echo [STOPPED] Protected portable Python is missing:
    echo %PORTABLE_PYTHON%
    pause
    exit /b 2
)
if not exist "%C3F_SCRIPT%" (
    echo [STOPPED] C3F preflight script is missing:
    echo %C3F_SCRIPT%
    pause
    exit /b 3
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "DO_NOT_TRACK=1"

"%PORTABLE_PYTHON%" -I -B -S "%C3F_SCRIPT%" --root "%FOXAI_ROOT%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo C3F finished successfully. Upload the generated review ZIP.
) else (
    echo C3F stopped safely with exit code %RC%.
    echo No launcher change or ComfyUI launch was performed.
)
echo.
pause
exit /b %RC%
