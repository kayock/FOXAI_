@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI Extension Manager Inventory and Health Phase 1

echo.
echo Package folder:
echo   %CD%
echo.

set "PY="
set "ARGS="

if exist "..\env\python\python.exe" (
  set "PY=..\env\python\python.exe"
) else if exist "..\python\python.exe" (
  set "PY=..\python\python.exe"
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    set "PY=py"
    set "ARGS=-3"
  ) else (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
  )
)

if not defined PY (
  echo ERROR: Python was not found.
  echo Extract the complete EMI1A folder directly inside Z:\FOXAI.
  pause
  exit /b 1
)

echo Python command:
echo   %PY% %ARGS%
echo.
echo Close FOXAI WebUI, Chat Engine, and benchmark servers first.
echo The apply requires the exact approval phrase.
echo Verified backup and rollback are mandatory.
echo.

call "%PY%" %ARGS% "%~dp0go.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
  echo The apply did not complete successfully.
  echo Nothing is considered installed unless the receipt says:
  echo   State: applied_verified
  echo   Verified: True
  if exist "%~dp0STARTUP_ERROR.txt" (
    echo.
    echo Startup diagnostic:
    echo   %~dp0STARTUP_ERROR.txt
  )
  pause
)

exit /b %RC%
