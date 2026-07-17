@echo off
setlocal
title FOXAI Portable Desktop Runtime Phase 3B - Exact Design
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

echo ========================================================================
echo FOXAI PORTABLE DESKTOP RUNTIME PHASE 3B
echo EXACT DESIGN - NO LIVE CHANGES
echo ========================================================================
echo.
echo Protected stable chain:
echo   Launch FOXAI Workshop shortcut
echo   Launch FOXAI Workshop.bat
echo   foxai.py
echo.
echo This step does not open the Desktop, install packages, alter either
echo shortcut, or replace the stable launcher.
echo.

if not exist "%PYTHON%" (
  echo [STOPPED] FOXAI bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -s "%~dp0design_desktop_runtime.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Desktop runtime exact design completed.
) else (
  echo [STOPPED] Design stopped fail-closed.
)
echo.
pause
exit /b %RESULT%
