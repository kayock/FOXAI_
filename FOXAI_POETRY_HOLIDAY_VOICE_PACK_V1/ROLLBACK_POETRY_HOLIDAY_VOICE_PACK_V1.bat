@echo off
setlocal EnableExtensions
title Roll Back FOXAI Poetry Holiday Voice Pack V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "LATEST=%FOXAI_ROOT%\Backups\PoetryHolidayVoicePackV1\LATEST.txt"
set "LIVE=%FOXAI_ROOT%\core\foxai_web.py"

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

copy /Y "%BACKUP%\core\foxai_web.py" "%LIVE%" >nul
echo Rollback completed. Restart FOXAI WebUI.
pause
