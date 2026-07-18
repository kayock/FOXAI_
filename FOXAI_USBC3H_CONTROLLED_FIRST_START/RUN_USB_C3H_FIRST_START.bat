@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0.") do set "PACKAGE_ROOT=%%~fI"
for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_ROOT%\System\FirstStart\usbc3h_controlled_first_start.py"

echo ================================================================
echo   FOXAI USB C3H - CONTROLLED FIRST START, HEALTH TEST, AND STOP
echo ================================================================
echo.
echo APPROVED LIVE ACTION:
echo - Start isolated ComfyUI in CPU mode
 echo - Disable all custom nodes
 echo - Listen only on 127.0.0.1:8188
 echo - Verify local health and capture logs
 echo - Stop ComfyUI before this gate completes
 echo.
echo FORBIDDEN:
echo - No launcher edits or dependency changes
 echo - No external listen address
 echo - No package install or network download
 echo - Do not leave ComfyUI running after the test
 echo.

if not exist "%PYTHON%" (
  echo [STOPPED] Portable Python is missing.
  pause
  exit /b 2
)
if not exist "%SCRIPT%" (
  echo [STOPPED] C3H control script is missing.
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
  echo [COMPLETE] C3H first start was healthy, verified, and stopped.
) else (
  echo [STOPPED] C3H exited with code %RC%. Review evidence before retrying.
)
echo ComfyUI should not be left running by this gate.
echo.
pause
exit /b %RC%
