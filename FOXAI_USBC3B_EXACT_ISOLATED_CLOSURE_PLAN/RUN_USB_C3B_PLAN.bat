@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ======================================================================
echo  FOXAI USB C3B - Exact Isolated Dependency Closure Plan
echo ======================================================================
echo.
echo NO-ACTION BOUNDARY:
echo - No package installs, uninstalls, or copying
echo - No wheel payload downloads
echo - No creation of Runtime\ComfyUI\site-packages
echo - No Desktop/Core/ComfyUI/launcher changes
echo - No FOXAI, WebUI, Desktop, or ComfyUI launch
echo - HTTPS network access is limited to PyPI JSON metadata at pypi.org
echo - Selected files.pythonhosted.org wheel URLs are recorded, not fetched
echo - Writes only new evidence under this package's PLAN_OUTPUT
echo.

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PORTABLE_PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "PLAN_SCRIPT=%~dp0System\Planning\usbc3b_exact_isolated_closure_plan.py"

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

if not exist "%PLAN_SCRIPT%" (
    echo [STOP] C3B planning script is missing:
    echo        %PLAN_SCRIPT%
    exit /b 4
)

if not exist "%FOXAI_ROOT%\FOXAI_USBC3A_COMFYUI_DEPENDENCY_PREFLIGHT\PREFLIGHT_OUTPUT" (
    echo [STOP] The reviewed C3A evidence folder is missing.
    echo        C3B will not proceed without exact C3A continuity verification.
    exit /b 5
)

set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONNOUSERSITE=1"
set "PIP_NO_INDEX=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "PYTHONHOME="

"%PORTABLE_PYTHON%" -B "%PLAN_SCRIPT%" --root "%FOXAI_ROOT%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [COMPLETE] C3B planning evidence is in PLAN_OUTPUT.
    echo Upload the newest timestamped output folder for exact review.
    echo Do not download wheels or create the target yet.
) else (
    echo [STOPPED] C3B failed closed with exit code %RC%.
    echo Upload the newest PLAN_OUTPUT folder for review.
)
exit /b %RC%
