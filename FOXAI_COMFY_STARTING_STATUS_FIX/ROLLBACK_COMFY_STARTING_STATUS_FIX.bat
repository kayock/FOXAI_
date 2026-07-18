@echo off
setlocal EnableExtensions
title Roll Back FOXAI ComfyUI Starting Status Fix

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "LATEST=%FOXAI_ROOT%\Backups\ComfyStartingStatusFix\LATEST.txt"

if not exist "%LATEST%" (
    echo No recorded backup was found.
    pause
    exit /b 2
)

set /p "BACKUP="<"%LATEST%"
if not exist "%BACKUP%\core\comfy_ops_monitor.py" (
    echo Backup unavailable:
    echo %BACKUP%
    pause
    exit /b 3
)

choice /C YN /N /M "Restore the previous two files? [Y/N]: "
if errorlevel 2 exit /b 0

copy /Y "%BACKUP%\core\comfy_ops_monitor.py" "%FOXAI_ROOT%\core\comfy_ops_monitor.py" >nul
copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul

echo Rollback completed.
pause
