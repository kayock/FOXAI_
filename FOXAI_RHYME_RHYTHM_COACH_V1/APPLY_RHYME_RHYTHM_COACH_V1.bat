@echo off
setlocal EnableExtensions
title FOXAI Rhyme and Rhythm Coach v1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "VERIFY=%~dp0verify_rhyme_rhythm_coach.py"

echo ============================================================
echo FOXAI RHYME AND RHYTHM COACH v1
echo ============================================================
echo Changes only:
echo   core\foxai_web.py
echo.
echo Adds:
echo - local stanza-by-stanza rhyme estimate
echo - estimated syllables for every line
echo - approximate rhyme scheme labels
echo - steady / uneven rhythm guidance
echo - AABB, ABAB, monorhyme, or rhythm-only targets
echo - direct handoff of one stanza to the Selection Workshop
echo.
echo Analysis is local and does not start the language model.
echo No poem is changed or saved by the Coach.
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
    echo ERROR: Portable Python was not found.
    pause
    exit /b 4
)

echo Close FOXAI WebUI before continuing.
choice /C YN /N /M "Apply this one-file backed-up Coach? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('powershell.exe -NoLogo -NoProfile -NonInteractive -Command "Get-Date -Format yyyyMMddTHHmmss"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\RhymeRhythmCoachV1\%STAMP%"
mkdir "%BACKUP%\core" 2>nul

copy /Y "%FOXAI_ROOT%\core\foxai_web.py" "%BACKUP%\core\foxai_web.py" >nul || goto :backup_failed
copy /Y "%PAYLOAD%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul || goto :apply_failed

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

"%PYTHON%" -I -B -S -m py_compile "%FOXAI_ROOT%\core\foxai_web.py"
if errorlevel 1 goto :compile_failed

"%PYTHON%" -I -B -S "%VERIFY%" "%FOXAI_ROOT%\core\foxai_web.py"
if errorlevel 1 goto :verify_failed

mkdir "%FOXAI_ROOT%\Backups\RhymeRhythmCoachV1" 2>nul
> "%FOXAI_ROOT%\Backups\RhymeRhythmCoachV1\LATEST.txt" echo %BACKUP%

echo.
echo ============================================================
echo RHYME AND RHYTHM COACH APPLIED AND VERIFIED
echo ============================================================
echo Backup:
echo   %BACKUP%
echo.
echo Restart WebUI, open Poetry Studio, and press:
echo   Check Rhyme and Rhythm
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
echo ERROR: Python syntax verification failed. Restoring backup...
goto :rollback

:verify_failed
echo ERROR: Coach verification failed. Restoring backup...
goto :rollback

:rollback
copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul
echo Rollback completed.
pause
exit /b 11
