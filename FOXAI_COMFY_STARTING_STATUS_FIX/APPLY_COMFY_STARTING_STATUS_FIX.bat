@echo off
setlocal EnableExtensions
title FOXAI ComfyUI Starting Status Fix

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo ============================================================
echo FOXAI ComfyUI Starting Status Fix
echo ============================================================
echo - Running but loading now displays STARTING, not OFFLINE.
echo - WebUI Status checks the real process and port.
echo - Raw stale-controller URL status errors are suppressed.
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
    echo ERROR: Extract this folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)

if not exist "%PYTHON%" (
    echo ERROR: Portable Python was not found.
    pause
    exit /b 3
)

echo Close FOXAI Desktop and WebUI before continuing.
echo ComfyUI itself may remain open.
choice /C YN /N /M "Apply the small backed-up correction? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('"%PYTHON%" -I -B -S -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%dT%%H%%M%%S'))"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\ComfyStartingStatusFix\%STAMP%"
mkdir "%BACKUP%\core" 2>nul

copy /Y "%FOXAI_ROOT%\core\comfy_ops_monitor.py" "%BACKUP%\core\comfy_ops_monitor.py" >nul || goto :backup_failed
copy /Y "%FOXAI_ROOT%\core\foxai_web.py" "%BACKUP%\core\foxai_web.py" >nul || goto :backup_failed

copy /Y "%PAYLOAD%\core\comfy_ops_monitor.py" "%FOXAI_ROOT%\core\comfy_ops_monitor.py" >nul || goto :apply_failed
copy /Y "%PAYLOAD%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul || goto :apply_failed

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
"%PYTHON%" -I -B -S -m py_compile ^
  "%FOXAI_ROOT%\core\comfy_ops_monitor.py" ^
  "%FOXAI_ROOT%\core\foxai_web.py"
if errorlevel 1 goto :compile_failed

mkdir "%FOXAI_ROOT%\Backups\ComfyStartingStatusFix" 2>nul
> "%FOXAI_ROOT%\Backups\ComfyStartingStatusFix\LATEST.txt" echo %BACKUP%

echo.
echo CORRECTION APPLIED AND SYNTAX VERIFIED.
echo Backup: %BACKUP%
echo.
echo Restart WebUI.
pause
exit /b 0

:backup_failed
echo ERROR: Backup failed. No files changed.
pause
exit /b 10

:apply_failed
echo ERROR: Copy failed. Restoring backup...
goto :rollback

:compile_failed
echo ERROR: Syntax verification failed. Restoring backup...
goto :rollback

:rollback
copy /Y "%BACKUP%\core\comfy_ops_monitor.py" "%FOXAI_ROOT%\core\comfy_ops_monitor.py" >nul
copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul
echo Rollback completed.
pause
exit /b 11
