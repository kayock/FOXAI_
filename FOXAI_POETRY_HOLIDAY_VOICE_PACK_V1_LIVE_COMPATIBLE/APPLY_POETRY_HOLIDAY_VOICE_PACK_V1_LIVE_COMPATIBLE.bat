@echo off
setlocal EnableExtensions
title FOXAI Poetry Holiday Voice Pack V1 - Live Compatible

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "LIVE=%FOXAI_ROOT%\core\foxai_web.py"
set "PAYLOAD=%~dp0payload\core\foxai_web.py"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "PREFLIGHT=%~dp0preflight_voice_pack.py"
set "VERIFY=%~dp0verify_voice_pack.py"

echo ============================================================
echo FOXAI HOLIDAY VOICE PACK V1 - LIVE COMPATIBLE
echo ============================================================
echo Built for the exact Rhyme Coach version currently installed.
echo.
echo Adds:
echo   Edgar Allan Poe - Gothic Lyric
echo   Beneath the Beats - West Coast Voice
echo   Dust and Duty - Last Gunslinger Voice
echo   The Forsaken Flame - Exile's Voice
echo.
echo Eric - Poet/Narrator and the current stanza tools are preserved.
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
    echo ERROR: Extract this folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)
if not exist "%LIVE%" (
    echo ERROR: Live WebUI file is missing.
    pause
    exit /b 3
)
if not exist "%PYTHON%" (
    echo ERROR: Portable Python was not found.
    pause
    exit /b 4
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

"%PYTHON%" -I -B -S "%PREFLIGHT%" "%LIVE%"
if errorlevel 20 (
    echo This pack is already installed.
    pause
    exit /b 0
)
if errorlevel 1 (
    echo Nothing was changed.
    pause
    exit /b 6
)

echo.
echo Close FOXAI WebUI before continuing.
choice /C YN /N /M "Apply this one-file backed-up voice pack? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('powershell.exe -NoLogo -NoProfile -NonInteractive -Command "Get-Date -Format yyyyMMddTHHmmss"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\PoetryHolidayVoicePackV1\%STAMP%"
mkdir "%BACKUP%\core" 2>nul

copy /Y "%LIVE%" "%BACKUP%\core\foxai_web.py" >nul || goto :backup_failed
copy /Y "%PAYLOAD%" "%LIVE%" >nul || goto :apply_failed

"%PYTHON%" -I -B -S -m py_compile "%LIVE%"
if errorlevel 1 goto :compile_failed

"%PYTHON%" -I -B -S "%VERIFY%" "%LIVE%"
if errorlevel 1 goto :verify_failed

mkdir "%FOXAI_ROOT%\Backups\PoetryHolidayVoicePackV1" 2>nul
> "%FOXAI_ROOT%\Backups\PoetryHolidayVoicePackV1\LATEST.txt" echo %BACKUP%

echo.
echo ============================================================
echo HOLIDAY VOICE PACK INSTALLED AND VERIFIED
echo ============================================================
echo Restart FOXAI WebUI and open Poetry Studio.
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
echo ERROR: Python syntax check failed. Restoring backup...
goto :rollback

:verify_failed
echo ERROR: Voice pack verification failed. Restoring backup...
goto :rollback

:rollback
copy /Y "%BACKUP%\core\foxai_web.py" "%LIVE%" >nul
echo Rollback completed.
pause
exit /b 11
