@echo off
setlocal EnableExtensions
title FOXAI Open Poem Project v1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "VERIFY=%~dp0verify_open_poem_project.py"

echo ============================================================
echo FOXAI OPEN POEM PROJECT v1
echo ============================================================
echo Changes only:
echo   core\foxai_web.py
echo.
echo Adds:
echo - Open Original in Poetry Studio
echo - Open Polished in Poetry Studio
echo - Duplicate as New Poem
echo - Open buttons in complete version history
echo - saved prompt and creation-field display
echo - full creator field persistence for future saves
echo - source-file lineage on reopened working copies
echo.
echo Reopened poems are working copies.
echo Saving always creates a new Markdown file.
echo Archived source files are never overwritten.
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
choice /C YN /N /M "Apply this one-file backed-up project update? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('powershell.exe -NoLogo -NoProfile -NonInteractive -Command "Get-Date -Format yyyyMMddTHHmmss"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\OpenPoemProjectV1\%STAMP%"
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

mkdir "%FOXAI_ROOT%\Backups\OpenPoemProjectV1" 2>nul
> "%FOXAI_ROOT%\Backups\OpenPoemProjectV1\LATEST.txt" echo %BACKUP%

echo.
echo ============================================================
echo OPEN POEM PROJECT v1 APPLIED AND VERIFIED
echo ============================================================
echo Backup:
echo   %BACKUP%
echo.
echo Restart WebUI and open:
echo   Kayock Writer ^> My Poems
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
echo ERROR: Open-project verification failed. Restoring backup...
goto :rollback

:rollback
copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul
echo Rollback completed.
pause
exit /b 11
