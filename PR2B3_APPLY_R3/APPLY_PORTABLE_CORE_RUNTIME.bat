@echo off
setlocal
title FOXAI Portable Core Runtime Phase 2B3 R3 - Guarded Apply
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

echo ================================================================
echo FOXAI PORTABLE CORE RUNTIME PHASE 2B3 - GUARDED APPLY
echo ================================================================
echo.
echo Exact approved changes:
echo   ADD     Runtime\Core\site-packages\**
echo   ADD     Runtime\Core\CORE_RUNTIME_MANIFEST.json
echo   MODIFY  env\python\python314._pth
echo   MODIFY  START_FOXAI_WEB_PORTABLE.bat
echo   DELETE  nothing
echo.
echo This does not start FOXAI.
echo It uses no network and performs no pip install.
echo.
set /p "CONFIRM=Type the exact approval phrase: "
if not "%CONFIRM%"=="APPROVE PORTABLE CORE RUNTIME PHASE 2B3 APPLY" (
  echo.
  echo [CANCELLED] Approval phrase did not match. No live changes made.
  pause
  exit /b 1
)

if not exist "%PYTHON%" (
  echo [STOPPED] Bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)

"%PYTHON%" -s "%~dp0apply_portable_core_runtime.py" --approval "%CONFIRM%"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [APPLIED AND VERIFIED] Portable core runtime is live.
) else (
  echo [STOPPED] Apply failed closed. Read the printed report path.
)
echo.
pause
exit /b %RESULT%
