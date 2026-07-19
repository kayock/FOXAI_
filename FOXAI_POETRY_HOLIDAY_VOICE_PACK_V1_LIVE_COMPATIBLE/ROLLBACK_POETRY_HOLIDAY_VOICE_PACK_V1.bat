@echo off
setlocal EnableExtensions
title Roll Back FOXAI Holiday Voice Pack V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "LATEST=%FOXAI_ROOT%\Backups\PoetryHolidayVoicePackV1\LATEST.txt"

if not exist "%LATEST%" (
    echo No recorded Holiday Voice Pack backup was found.
    pause
    exit /b 2
)

set /p "BACKUP="<"%LATEST%"
if not exist "%BACKUP%\core\foxai_web.py" (
    echo Backup unavailable:
    echo %BACKUP%
    pause
    exit /b 3
)

choice /C YN /N /M "Restore the previous Poetry Studio WebUI? [Y/N]: "
if errorlevel 2 exit /b 0

copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul
echo Rollback completed. Restart FOXAI WebUI.
pause
