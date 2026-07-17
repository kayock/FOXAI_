@echo off
setlocal
title FOXAI Portable Runtime Phase 2B2 - Wheelhouse Acquisition
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

echo ================================================================
echo FOXAI PORTABLE RUNTIME PHASE 2B2
echo QUARANTINED CORE WHEELHOUSE ACQUISITION
echo ================================================================
echo.
echo This will download 12 exact wheels from files.pythonhosted.org.
echo It will NOT install them into the live FOXAI runtime.
echo It will NOT change launchers, source, config, registry, or Python paths.
echo.
set /p "CONFIRM=Type ACQUIRE CORE WHEELHOUSE to continue: "
if not "%CONFIRM%"=="ACQUIRE CORE WHEELHOUSE" (
  echo.
  echo [CANCELLED] No downloads were started.
  pause
  exit /b 1
)

if not exist "%PYTHON%" (
  echo [STOPPED] Bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)

"%PYTHON%" -s "%~dp0acquire_core_wheelhouse.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Quarantined core wheelhouse passed.
) else (
  echo [STOPPED] Acquisition failed closed. Files remain in quarantine.
)
echo.
pause
exit /b %RESULT%
