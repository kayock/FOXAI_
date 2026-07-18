@echo off
setlocal EnableExtensions
title Roll Back FOXAI Red Canvas Live Progress Fix

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "LATEST=%FOXAI_ROOT%\Backups\RedCanvasLiveProgress\LATEST.txt"

if not exist "%LATEST%" (
    echo No recorded backup was found.
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

choice /C YN /N /M "Restore the previous Desktop file? [Y/N]: "
if errorlevel 2 exit /b 0

copy /Y "%BACKUP%\ui\main_window.py" "%FOXAI_ROOT%\ui\main_window.py" >nul
echo Rollback completed.
pause
