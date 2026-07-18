@echo off
setlocal EnableExtensions
title Roll Back FOXAI Poetry Studio v1 Finish

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "LATEST=%FOXAI_ROOT%\Backups\PoetryStudioV1Finish\LATEST.txt"

if not exist "%LATEST%" (
    echo No recorded Poetry Studio backup was found.
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

choice /C YN /N /M "Restore the previous WebUI file? [Y/N]: "
if errorlevel 2 (
    echo Cancelled.
    pause
    exit /b 0
)

copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul
echo Rollback completed.
pause
