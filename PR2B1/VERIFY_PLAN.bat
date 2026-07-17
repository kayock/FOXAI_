@echo off
setlocal
title FOXAI Portable Runtime Phase 2B1 - Verify Manifest
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

echo ================================================================
echo FOXAI PORTABLE RUNTIME PHASE 2B1 - VERIFY MANIFEST
echo ================================================================
echo.

if not exist "%PYTHON%" (
  echo [STOPPED] Bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)

"%PYTHON%" -s "%~dp0verify_plan.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Core wheelhouse manifest is ready.
) else (
  echo [STOPPED] Verification failed closed.
)
echo.
pause
exit /b %RESULT%
