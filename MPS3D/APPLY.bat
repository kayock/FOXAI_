@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title FOXAI Phase 3 Transactional Apply

set "PYTHON_EXE="
set "PYTHON_ARGS="

if exist "..\env\python\python.exe" (
  set "PYTHON_EXE=..\env\python\python.exe"
) else if exist "..\python\python.exe" (
  set "PYTHON_EXE=..\python\python.exe"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
  ) else (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_EXE=python"
  )
)

echo.
echo ========================================================================
echo FOXAI MODEL PROFILE SELECTOR + VERIFIED RUNTIME
echo PHASE 3 TRANSACTIONAL APPLY — STAY-OPEN V2
echo ========================================================================
echo.
echo Package folder:
echo   %CD%
echo.

if not defined PYTHON_EXE (
  echo ERROR: Python was not found.
  echo.
  echo Extract this COMPLETE folder directly inside:
  echo   Z:\FOXAI\
  echo.
  echo Do not run the BAT from inside the ZIP preview window.
  echo.
  pause
  exit /b 1
)

if not exist "%~dp0apply_model_profile_selector_runtime_phase3.py" (
  echo ERROR: The main apply script is missing from this folder.
  echo The package may not have been fully extracted.
  echo.
  pause
  exit /b 1
)

if not exist "%~dp0phase3_verifier.py" (
  echo ERROR: phase3_verifier.py is missing from this folder.
  echo The package may not have been fully extracted.
  echo.
  pause
  exit /b 1
)

echo Python command:
echo   %PYTHON_EXE% %PYTHON_ARGS%
echo.
call "%PYTHON_EXE%" %PYTHON_ARGS% --version
if errorlevel 1 (
  echo.
  echo ERROR: The selected Python command could not start.
  echo.
  pause
  exit /b 1
)

echo.
echo Close FOXAI WebUI, Chat Engine, and any benchmark server first.
echo The apply requires the exact approval phrase.
echo Verified backup and rollback are mandatory.
echo.
echo Starting verified preflight...
echo.

call "%PYTHON_EXE%" %PYTHON_ARGS% "%~dp0go.py"
set "APPLY_RC=%ERRORLEVEL%"

echo.
echo ========================================================================
echo APPLY PROCESS EXIT CODE: %APPLY_RC%
echo ========================================================================

if not "%APPLY_RC%"=="0" (
  echo.
  echo The apply did not complete successfully.
  echo Nothing is considered installed unless the receipt says:
  echo   State: applied_verified
  echo   Verified: True
  echo.
  if exist "%~dp0APPLY_STARTUP_ERROR.txt" (
    echo Startup diagnostic:
    echo   %~dp0APPLY_STARTUP_ERROR.txt
    echo.
    type "%~dp0APPLY_STARTUP_ERROR.txt"
    echo.
  )
  pause
)

exit /b %APPLY_RC%
