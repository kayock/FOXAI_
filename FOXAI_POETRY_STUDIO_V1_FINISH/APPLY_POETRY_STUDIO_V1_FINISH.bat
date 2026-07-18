@echo off
setlocal EnableExtensions
title FOXAI Poetry Studio v1 Finish

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo ============================================================
echo FOXAI POETRY STUDIO V1 FINISH
echo ============================================================
echo Changes only:
echo   core\foxai_web.py
echo.
echo Adds:
echo - separately generated poem titles
echo - clear CREATING, POLISHING, READY TO COMPARE, and SAVED states
echo - disabled conflicting controls while the model is working
echo - Light Touch, Balanced, and Bold Rewrite polishing strengths
echo - Keep Original, Use Polished Version, and Save Both
echo - separate original and polished Markdown files
echo - microsecond filenames so drafts never overwrite one another
echo.
echo No new dependencies, model changes, migrations, or deletes.
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
    echo ERROR: Extract this folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)

if not exist "%FOXAI_ROOT%\core\foxai_web.py" (
    echo ERROR: Live WebUI file is missing:
    echo %FOXAI_ROOT%\core\foxai_web.py
    pause
    exit /b 3
)

if not exist "%PYTHON%" (
    echo ERROR: Portable Python was not found:
    echo %PYTHON%
    pause
    exit /b 4
)

echo Close FOXAI WebUI before continuing.
echo Desktop and ComfyUI may remain open.
choice /C YN /N /M "Apply the small backed-up Poetry Studio update? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('"%PYTHON%" -I -B -S -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%dT%%H%%M%%S'))"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\PoetryStudioV1Finish\%STAMP%"
mkdir "%BACKUP%\core" 2>nul

copy /Y "%FOXAI_ROOT%\core\foxai_web.py" "%BACKUP%\core\foxai_web.py" >nul || goto :backup_failed
copy /Y "%PAYLOAD%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul || goto :apply_failed

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
"%PYTHON%" -I -B -S -m py_compile "%FOXAI_ROOT%\core\foxai_web.py"
if errorlevel 1 goto :compile_failed

mkdir "%FOXAI_ROOT%\Backups\PoetryStudioV1Finish" 2>nul
> "%FOXAI_ROOT%\Backups\PoetryStudioV1Finish\LATEST.txt" echo %BACKUP%

echo.
echo ============================================================
echo POETRY STUDIO V1 FINISH APPLIED AND SYNTAX VERIFIED
echo ============================================================
echo Backup: %BACKUP%
echo.
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
echo ERROR: Python syntax verification failed. Restoring backup...
goto :rollback

:rollback
copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul
echo Rollback completed.
pause
exit /b 11
