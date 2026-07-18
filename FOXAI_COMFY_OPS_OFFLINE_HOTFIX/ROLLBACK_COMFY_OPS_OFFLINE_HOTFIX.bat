@echo off
setlocal EnableExtensions
title Roll Back FOXAI ComfyUI Offline Display Hotfix

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "LATEST=%FOXAI_ROOT%\Backups\ComfyOpsOfflineHotfix\LATEST.txt"

if not exist "%LATEST%" (
    echo No recorded hotfix backup was found.
    pause
    exit /b 2
)

set /p "BACKUP="<"%LATEST%"
if not exist "%BACKUP%\ui\main_window.py" (
    echo Backup unavailable:
    echo %BACKUP%
    pause
    exit /b 3
)

choice /C YN /N /M "Restore the previous monitor files? [Y/N]: "
if errorlevel 2 (
    echo Cancelled.
    pause
    exit /b 0
)

copy /Y "%BACKUP%\ui\main_window.py" "%FOXAI_ROOT%\ui\main_window.py" >nul
copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul
copy /Y "%BACKUP%\core\comfy_ops_monitor.py" "%FOXAI_ROOT%\core\comfy_ops_monitor.py" >nul

echo Rollback completed.
pause
