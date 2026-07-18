@echo off
setlocal EnableExtensions
title FOXAI Red Canvas Live Progress Fix

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo ============================================================
echo FOXAI RED CANVAS LIVE PROGRESS FIX
echo ============================================================
echo This changes only ui\main_window.py.
echo The purple bar will read the real percentage already written
echo by the green ComfyUI Operations console.
echo.
echo No launcher, model, workflow, WebUI, or ComfyUI changes.
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

echo Close FOXAI Desktop before continuing.
echo The WebUI and ComfyUI may remain open.
choice /C YN /N /M "Apply the small backed-up fix? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('"%PYTHON%" -I -B -S -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%dT%%H%%M%%S'))"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\RedCanvasLiveProgress\%STAMP%"
mkdir "%BACKUP%\ui" 2>nul

copy /Y "%FOXAI_ROOT%\ui\main_window.py" "%BACKUP%\ui\main_window.py" >nul || goto :backup_failed
copy /Y "%PAYLOAD%\ui\main_window.py" "%FOXAI_ROOT%\ui\main_window.py" >nul || goto :apply_failed

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
"%PYTHON%" -I -B -S -m py_compile "%FOXAI_ROOT%\ui\main_window.py"
if errorlevel 1 goto :compile_failed

mkdir "%FOXAI_ROOT%\Backups\RedCanvasLiveProgress" 2>nul
> "%FOXAI_ROOT%\Backups\RedCanvasLiveProgress\LATEST.txt" echo %BACKUP%

echo.
echo LIVE PROGRESS FIX APPLIED AND SYNTAX VERIFIED.
echo Backup: %BACKUP%
echo.
echo Restart FOXAI Desktop and generate one image.
echo The bar should remain at 0 while the model loads, then match
echo the green console at 5, 10, 15 percent and onward.
echo.
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
copy /Y "%BACKUP%\ui\main_window.py" "%FOXAI_ROOT%\ui\main_window.py" >nul
echo Rollback completed.
pause
exit /b 11
