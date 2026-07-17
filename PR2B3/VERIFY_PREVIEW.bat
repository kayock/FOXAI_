@echo off
setlocal
title FOXAI Portable Runtime Phase 2B3 - Exact Preview
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

echo ================================================================
echo FOXAI PORTABLE RUNTIME PHASE 2B3 - EXACT PREVIEW
echo ================================================================
echo.
echo This reconstructs the candidate only inside PR2B3\candidate.
echo It does not modify the live runtime, launcher, source, or config.
echo.

if not exist "%PYTHON%" (
  echo [STOPPED] Bundled Python was not found.
  pause
  exit /b 2
)

"%PYTHON%" -s "%~dp0verify_preview.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Exact preview passed.
) else (
  echo [STOPPED] Exact preview failed closed.
)
echo.
pause
exit /b %RESULT%
