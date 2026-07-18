@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ======================================================================
echo  FOXAI USB C3C - Exact Wheel Acquisition and Cryptographic Staging
echo ======================================================================
echo.
echo AUTHORIZED BOUNDARY:
echo - Revalidate exact C3B package metadata at pypi.org
echo - Download only exact reviewed wheel URLs from files.pythonhosted.org
echo - Verify exact size, SHA-256, compatible tags, ZIP structure, and RECORD
echo - Stage accepted wheels only inside this C3C package
echo - Write evidence only inside this C3C package
echo.
echo FORBIDDEN:
echo - No pip or uv install, uninstall, upgrade, or downgrade
echo - No source archives or local builds
echo - No Runtime\ComfyUI\site-packages creation or modification
echo - No Runtime\ComfyUI\wheelhouse creation or modification
echo - No Desktop, Core, ComfyUI, System, or launcher changes
echo - No FOXAI, WebUI, Desktop, or ComfyUI launch
echo.
echo A successful run may download approximately 0.669 GiB of exact wheel files.
echo Interrupted runs preserve accepted wheels for exact reuse and fail closed.
echo.

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PORTABLE_PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "ACQUIRE_SCRIPT=%~dp0System\Acquisition\usbc3c_exact_wheel_acquisition.py"

if not exist "%FOXAI_ROOT%\ComfyUI\main.py" (
    echo [STOP] Could not verify FOXAI root at:
    echo        %FOXAI_ROOT%
    echo.
    echo Extract this complete folder directly inside the FOXAI root, then rerun.
    exit /b 2
)

if not exist "%PORTABLE_PYTHON%" (
    echo [STOP] Verified Desktop portable Python is missing:
    echo        %PORTABLE_PYTHON%
    exit /b 3
)

if not exist "%ACQUIRE_SCRIPT%" (
    echo [STOP] C3C acquisition script is missing:
    echo        %ACQUIRE_SCRIPT%
    exit /b 4
)

if not exist "%FOXAI_ROOT%\FOXAI_USBC3B_EXACT_ISOLATED_CLOSURE_PLAN\PLAN_OUTPUT" (
    echo [STOP] The reviewed C3B PLAN_OUTPUT folder is missing.
    echo        C3C will not proceed without exact reviewed C3B continuity.
    exit /b 5
)

if exist "%FOXAI_ROOT%\Runtime\ComfyUI\site-packages" (
    echo [STOP] Runtime\ComfyUI\site-packages already exists.
    echo        C3C refuses this ambiguous state and will not alter it.
    exit /b 6
)

set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONNOUSERSITE=1"
set "PIP_NO_INDEX=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "PYTHONHOME="

"%PORTABLE_PYTHON%" -B "%ACQUIRE_SCRIPT%" --root "%FOXAI_ROOT%"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo [COMPLETE] C3C exact wheel staging completed.
    echo Upload UPLOAD_THIS_C3C_REVIEW.zip from the newest ACQUISITION_OUTPUT folder.
    echo Do not create the isolated target or install packages yet.
) else (
    echo [STOPPED] C3C failed closed with exit code %RC%.
    echo Upload UPLOAD_THIS_C3C_REVIEW.zip from the newest ACQUISITION_OUTPUT folder.
    echo Do not install packages or create the isolated target.
)
exit /b %RC%
