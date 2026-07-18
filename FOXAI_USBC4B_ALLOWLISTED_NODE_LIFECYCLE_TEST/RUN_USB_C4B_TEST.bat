@echo off
setlocal EnableExtensions DisableDelayedExpansion
for %%I in ("%~dp0.") do set "PACKAGE_ROOT=%%~fI"
for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_ROOT%\System\NodeTest\usbc4b_allowlisted_node_lifecycle_test.py"

echo ==================================================================
echo   FOXAI USB C4B - ALLOWLISTED CUSTOM-NODE LIFECYCLE TEST
echo ==================================================================
echo.
echo APPROVED LIVE ACTION:
echo - CPU mode on 127.0.0.1:8188 only
echo - Disable all custom nodes, then whitelist exactly websocket_image_save.py
echo - Verify registration, health, audit events, and process ownership
echo - Stop ComfyUI before the test completes
echo.
echo FORBIDDEN:
echo - No WebUI or launcher changes
echo - No external network access or package installation
echo - No unreviewed custom-node import
echo - Do not leave ComfyUI running
echo.

if not exist "%PYTHON%" (
  echo [STOPPED] Portable Python is missing.
  pause
  exit /b 2
)
if not exist "%SCRIPT%" (
  echo [STOPPED] C4B control script is missing.
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
  echo [COMPLETE] C4B allowlisted node imported, registered, verified, and stopped.
) else (
  echo [STOPPED] C4B exited with code %RC%. Review evidence before retrying.
)
echo ComfyUI should not be left running by this gate.
echo.
pause
exit /b %RC%
