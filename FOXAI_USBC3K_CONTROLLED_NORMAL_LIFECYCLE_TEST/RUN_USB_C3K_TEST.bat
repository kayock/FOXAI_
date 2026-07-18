@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0.") do set "PACKAGE_ROOT=%%~fI"
for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_ROOT%\System\LifecycleTest\usbc3k_controlled_normal_lifecycle_test.py"

echo ================================================================
echo   FOXAI USB C3K - CONTROLLED NORMAL LIFECYCLE TEST
echo ================================================================
echo.
echo APPROVED LIVE SEQUENCE:
echo - Confirm STOPPED
echo - Start Safe Normal CPU without opening a browser
echo - Confirm exact controller ownership and HEALTHY localhost service
echo - Request graceful stop through the installed normal controller
echo - Confirm STOPPED and port 8188 closed
echo.
echo FORBIDDEN:
echo - No launcher or runtime edits
echo - No custom nodes
echo - No external listen address
echo - No force-kill
echo - Do not leave ComfyUI running
echo.
if not exist "%PYTHON%" (
  echo [STOPPED] Portable Python is missing.
  pause
  exit /b 2
)
if not exist "%SCRIPT%" (
  echo [STOPPED] C3K test script is missing.
  pause
  exit /b 3
)
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --package-root "%PACKAGE_ROOT%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [COMPLETE] C3K normal lifecycle passed and ComfyUI is stopped.
) else (
  echo [STOPPED] C3K exited with code %RC%. Review evidence before retrying.
)
echo ComfyUI must be STOPPED when this window closes.
echo.
pause
exit /b %RC%
