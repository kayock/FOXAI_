@echo off
setlocal
title FOXAI Portable Host Model Library Phase 2C1 - Read-Only Audit
cd /d "%~dp0"
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\env\python\python.exe"

echo ================================================================
echo FOXAI PORTABLE HOST MODEL LIBRARY PHASE 2C1
echo READ-ONLY MODEL SOURCES AND MACHINE PROFILES AUDIT
echo ================================================================
echo.
echo This audit:
echo   - inspects current model selector and launch logic;
echo   - inventories approved C:\KayockModels folders;
echo   - does not start a model or contact an online provider;
echo   - does not hash, copy, move, rename, or delete GGUF files;
echo   - changes no source, config, launcher, credential, or registry.
echo.

if not exist "%PYTHON%" (
  echo [STOPPED] Bundled Python was not found:
  echo %PYTHON%
  pause
  exit /b 2
)

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -s "%~dp0audit_host_model_library.py"
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
  echo [VERIFIED] Host model library audit completed.
) else (
  echo [STOPPED] Audit failed closed.
)
echo.
pause
exit /b %RESULT%
