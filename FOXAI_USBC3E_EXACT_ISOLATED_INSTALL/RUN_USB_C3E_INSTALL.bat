@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "RC=0"

echo ======================================================================
echo  FOXAI USB C3E R2 - Exact Isolated Installation / Verified Resume
echo ======================================================================
echo.
echo APPROVED WRITE BOUNDARY:
echo - Resume the one exact preserved C3E staging target when prior evidence verifies it
echo - Otherwise create one new adjacent .C3E_site-packages_staging_UTC directory
echo - Offline exact installation of the 96 reviewed wheels only when no valid staging exists
echo - Full portable-Python verification
echo - Same-volume rename to Runtime\ComfyUI\site-packages only after all gates pass
echo - Evidence only inside this C3E package
echo.
echo FORBIDDEN:
echo - No network access or package resolution
echo - No Desktop, Core, host Python, ComfyUI source, System, or launcher changes
echo - No Runtime\ComfyUI\wheelhouse creation
echo - No FOXAI, WebUI, Desktop, or ComfyUI launch
echo - No overwrite, merge, uninstall, automatic cleanup, or automatic rollback
echo.
echo This window will remain open at the end so you can read the result.
echo.

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PORTABLE_PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "INSTALL_SCRIPT=%~dp0System\Installation\usbc3e_exact_isolated_install.py"

if not exist "%FOXAI_ROOT%\ComfyUI\main.py" (
    echo [STOP] Could not verify FOXAI root at:
    echo        %FOXAI_ROOT%
    set "RC=2"
    goto :finish
)
if not exist "%PORTABLE_PYTHON%" (
    echo [STOP] Protected portable Python is missing:
    echo        %PORTABLE_PYTHON%
    set "RC=3"
    goto :finish
)
if not exist "%INSTALL_SCRIPT%" (
    echo [STOP] C3E installation script is missing:
    echo        %INSTALL_SCRIPT%
    set "RC=4"
    goto :finish
)
if not exist "%FOXAI_ROOT%\FOXAI_USBC3D_EXACT_ISOLATED_INSTALL_PLAN\PLAN_OUTPUT" (
    echo [STOP] Reviewed C3D evidence is missing.
    set "RC=5"
    goto :finish
)
if not exist "%FOXAI_ROOT%\FOXAI_USBC3C_EXACT_WHEEL_ACQUISITION\STAGING_WHEELHOUSE" (
    echo [STOP] Reviewed C3C staging wheelhouse is missing.
    set "RC=6"
    goto :finish
)
if exist "%FOXAI_ROOT%\Runtime\ComfyUI\site-packages" (
    echo [STOP] Runtime\ComfyUI\site-packages already exists.
    echo C3E refuses to overwrite or merge into an existing target.
    set "RC=7"
    goto :finish
)
if exist "%FOXAI_ROOT%\Runtime\ComfyUI\wheelhouse" (
    echo [STOP] Runtime\ComfyUI\wheelhouse unexpectedly exists.
    set "RC=8"
    goto :finish
)

set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONNOUSERSITE=1"
set "PIP_CONFIG_FILE=NUL"
set "PIP_NO_INDEX=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "HF_DATASETS_OFFLINE=1"
set "NO_PROXY=*"
set "PYTHONHOME="
set "PYTHONPATH="

"%PORTABLE_PYTHON%" -I -B "%INSTALL_SCRIPT%" --root "%FOXAI_ROOT%"
set "RC=%ERRORLEVEL%"

:finish
echo.
if "%RC%"=="0" (
    echo [COMPLETE] C3E installed, verified, and committed the isolated target.
    echo Upload UPLOAD_THIS_C3E_REVIEW.zip from the newest INSTALL_OUTPUT folder.
    echo Do not edit launchers or launch ComfyUI until exact C3E review is complete.
) else (
    echo [STOPPED] C3E failed closed with exit code %RC%.
    echo Upload UPLOAD_THIS_C3E_REVIEW.zip from the newest INSTALL_OUTPUT folder.
    echo Do not delete or alter any preserved C3E staging or final target.
)
echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%
