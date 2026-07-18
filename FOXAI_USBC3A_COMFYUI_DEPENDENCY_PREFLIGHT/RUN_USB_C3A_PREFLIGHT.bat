@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ================================================================
echo  FOXAI USB C3A - ComfyUI Dependency/Binary Preflight
echo ================================================================
echo.
echo READ-ONLY BOUNDARY:
echo - No installs or downloads
echo - No dependency or package copying
echo - No launcher changes
echo - No FOXAI, Desktop, WebUI, or ComfyUI launch
echo - No creation of Runtime\ComfyUI\site-packages
echo - Writes only new evidence under this package's PREFLIGHT_OUTPUT
echo.

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PORTABLE_PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "PREFLIGHT_SCRIPT=%~dp0System\Preflight\usbc3a_comfy_dependency_preflight.py"

if not exist "%FOXAI_ROOT%\ComfyUI\main.py" (
    echo [STOP] Could not verify FOXAI root at:
    echo        %FOXAI_ROOT%
    echo.
    echo Extract this entire folder directly inside the FOXAI root, then rerun.
    exit /b 2
)

if not exist "%PORTABLE_PYTHON%" (
    echo [STOP] Verified Desktop portable Python is missing:
    echo        %PORTABLE_PYTHON%
    exit /b 3
)

if not exist "%PREFLIGHT_SCRIPT%" (
    echo [STOP] C3A preflight script is missing:
    echo        %PREFLIGHT_SCRIPT%
    exit /b 4
)

set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONNOUSERSITE=1"
set "PIP_NO_INDEX=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "NO_PROXY=*"
set "PYTHONHOME="

"%PORTABLE_PYTHON%" -B "%PREFLIGHT_SCRIPT%" --root "%FOXAI_ROOT%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [COMPLETE] C3A evidence is in PREFLIGHT_OUTPUT.
    echo Upload the newest timestamped output folder for exact review.
) else (
    echo [STOPPED] C3A failed closed with exit code %RC%.
    echo Review the newest receipt and classification in PREFLIGHT_OUTPUT.
)
exit /b %RC%
