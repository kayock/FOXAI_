@echo off
setlocal EnableExtensions
title FOXAI Eric Voice Exact Live Fix

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo ============================================================
echo FOXAI ERIC VOICE - EXACT LIVE FIX
echo ============================================================
echo This directly replaces only:
echo   core\foxai_web.py
echo.
echo The complete Eric voice profile is embedded in that one file.
echo No second module or dependency is required.
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
    echo ERROR: Extract this folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)
if not exist "%FOXAI_ROOT%\core\foxai_web.py" (
    echo ERROR: Live WebUI file is missing.
    pause
    exit /b 3
)
if not exist "%PYTHON%" (
    echo ERROR: Portable Python is missing.
    pause
    exit /b 4
)

echo Close FOXAI WebUI before continuing.
choice /C YN /N /M "Apply this one-file backed-up fix? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('powershell.exe -NoLogo -NoProfile -NonInteractive -Command "Get-Date -Format yyyyMMddTHHmmss"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\EricVoiceExactLiveFix\%STAMP%"
mkdir "%BACKUP%\core" 2>nul

copy /Y "%FOXAI_ROOT%\core\foxai_web.py" "%BACKUP%\core\foxai_web.py" >nul || goto :backup_failed
copy /Y "%PAYLOAD%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul || goto :apply_failed

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
"%PYTHON%" -I -B -S -m py_compile "%FOXAI_ROOT%\core\foxai_web.py"
if errorlevel 1 goto :compile_failed

mkdir "%FOXAI_ROOT%\Backups\EricVoiceExactLiveFix" 2>nul
> "%FOXAI_ROOT%\Backups\EricVoiceExactLiveFix\LATEST.txt" echo %BACKUP%

echo.
echo ============================================================
echo ERIC VOICE EXACT LIVE FIX APPLIED
echo ============================================================
echo Backup: %BACKUP%
echo.
echo Restart WebUI. Eric - Poet/Narrator will appear directly
echo below My natural voice.
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
copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul
echo Rollback completed.
pause
exit /b 11
