@echo off
setlocal
title FOXAI Portable Desktop Runtime Phase 3A - Read-Only Audit
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

echo ========================================================================
echo FOXAI PORTABLE DESKTOP RUNTIME PHASE 3A
echo READ-ONLY AUDIT
echo ========================================================================
echo.
echo This audit inspects the stable Desktop launch chain and runtime.
echo It will not open the Desktop GUI, run pip, install packages, or change
echo the shortcut, launcher, source, models, WebUI, or ComfyUI.
echo.

if not exist "%PYTHON%" (
  echo [STOPPED] FOXAI bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -s "%~dp0audit_desktop_runtime.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Desktop runtime audit completed.
) else (
  echo [STOPPED] Audit failed closed. Read the printed report path.
)
echo.
pause
exit /b %RESULT%
