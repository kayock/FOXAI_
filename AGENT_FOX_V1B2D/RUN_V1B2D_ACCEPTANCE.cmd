@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "PYTHON=Z:\FOXAI\Runtime\Desktop\python\python.exe"
set "RUNNER=%~dp0run_v1b2d_acceptance.py"

echo.
echo AGENT FOX TECHNICAL CORE V1B-2D
echo DUAL-INTERFACE LIVE ACCEPTANCE VERIFICATION
echo Mission: ENG-20260722-183657-F5AF85
echo ------------------------------------------------------------
echo This runs installed WebUI and Desktop route helpers directly.
echo It does not launch either GUI, load a model, scan live state,
echo use the network, alter source files, or access K:.
echo.

if not exist "%PYTHON%" (
  echo [BLOCKED] Portable Desktop Python was not found:
  echo %PYTHON%
  goto :fail
)
if not exist "%RUNNER%" (
  echo [BLOCKED] Acceptance runner was not found:
  echo %RUNNER%
  goto :fail
)

"%PYTHON%" -I -B -S "%RUNNER%"
if errorlevel 1 goto :fail

echo.
echo [VERIFIED] V1B-2D acceptance completed successfully.
echo Copy the JSON result above and return it to Sol.
echo.
pause
exit /b 0

:fail
echo.
echo [BLOCKED] Acceptance did not complete. No live source change was requested.
echo Copy the complete output above and return it to Sol.
echo.
pause
exit /b 1
