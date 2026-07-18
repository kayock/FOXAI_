@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ======================================================================
echo  FOXAI USB C3D R1 - Exact Isolated Installation Plan and Approval Preflight
echo ======================================================================
echo.
echo AUTHORIZED BOUNDARY:
echo - Re-hash and inspect the exact reviewed C3C staging wheelhouse
echo - Verify the exact reviewed C3B installation order
echo - Probe portable pip first; if absent, verify exact host CPython 3.14.6 / pip 26.1.2
echo - Run the selected pip engine only with --dry-run, --no-index, --no-deps, local hash-locked wheels
echo - Write plan evidence only inside this C3D package
echo.
echo FORBIDDEN:
echo - No Runtime\ComfyUI\site-packages or transaction-target creation
echo - No package installation, uninstall, build, extraction, or package copy
echo - No network access
echo - No Desktop, Core, ComfyUI source, System, or launcher changes
echo - No FOXAI, WebUI, Desktop, or ComfyUI launch
echo.

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PORTABLE_PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "PLAN_SCRIPT=%~dp0System\Planning\usbc3d_exact_isolated_install_plan.py"

if not exist "%FOXAI_ROOT%\ComfyUI\main.py" (
    echo [STOP] Could not verify FOXAI root at:
    echo        %FOXAI_ROOT%
    echo Extract this complete folder directly inside the FOXAI root, then rerun.
    exit /b 2
)
if not exist "%PORTABLE_PYTHON%" (
    echo [STOP] Verified Desktop portable Python is missing:
    echo        %PORTABLE_PYTHON%
    exit /b 3
)
if not exist "%PLAN_SCRIPT%" (
    echo [STOP] C3D planning script is missing:
    echo        %PLAN_SCRIPT%
    exit /b 4
)
if not exist "%FOXAI_ROOT%\FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION\STAGING_WHEELHOUSE" (
    echo [STOP] The reviewed C3C staging wheelhouse is missing.
    exit /b 5
)
if not exist "%FOXAI_ROOT%\FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION\ACQUISITION_OUTPUT" (
    echo [STOP] The reviewed C3C evidence folder is missing.
    exit /b 6
)
if not exist "%FOXAI_ROOT%\FOXAI_USBC3B_EXACT_ISOLATED_CLOSURE_PLAN\PLAN_OUTPUT" (
    echo [STOP] The reviewed C3B plan evidence is missing.
    exit /b 7
)
if exist "%FOXAI_ROOT%\Runtime\ComfyUI\site-packages" (
    echo [STOP] Runtime\ComfyUI\site-packages already exists.
    echo C3D refuses this ambiguous state and will not alter it.
    exit /b 8
)
if exist "%FOXAI_ROOT%\Runtime\ComfyUI\wheelhouse" (
    echo [STOP] Runtime\ComfyUI\wheelhouse unexpectedly exists.
    echo C3D refuses this ambiguous state and will not alter it.
    exit /b 9
)

set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONNOUSERSITE=1"
set "PIP_CONFIG_FILE=NUL"
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
    echo [COMPLETE] C3D exact isolated installation plan completed.
    echo Upload UPLOAD_THIS_C3D_REVIEW.zip from the newest PLAN_OUTPUT folder.
    echo Do not create the isolated target or install packages yet.
) else (
    echo [STOPPED] C3D failed closed with exit code %RC%.
    echo Upload UPLOAD_THIS_C3D_REVIEW.zip from the newest PLAN_OUTPUT folder.
    echo Do not create or install the isolated target.
)
exit /b %RC%
