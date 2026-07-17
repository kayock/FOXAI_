@echo off
setlocal
title FOXAI Portable Runtime Phase 2B2 - Verify Package
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"
if not exist "%PYTHON%" (
  echo [STOPPED] Bundled Python was not found.
  pause
  exit /b 2
)
"%PYTHON%" -s "%~dp0verify_package.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Acquisition package is ready.
) else (
  echo [STOPPED] Verification failed closed.
)
echo.
pause
exit /b %RESULT%
