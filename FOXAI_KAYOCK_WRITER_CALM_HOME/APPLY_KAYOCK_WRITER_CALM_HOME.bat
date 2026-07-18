@echo off
setlocal EnableExtensions
title FOXAI Kayock Writer Calm Home

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo ============================================================
echo FOXAI KAYOCK WRITER CALM HOME
echo ============================================================
echo Changes only:
echo   core\foxai_web.py
echo.
echo Adds:
echo - calm Writer home with four understandable rooms
echo - working Poetry Studio Poem Creator and Polisher
echo - D-and-D focused World Builder guided entry points
echo - simple My Writing page
echo - collapsed Writer Advanced Tools
echo.
echo No new dependencies, file migration, model changes, or deletes.
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
choice /C YN /N /M "Apply the small backed-up Writer update? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('"%PYTHON%" -I -B -S -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%dT%%H%%M%%S'))"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\KayockWriterCalmHome\%STAMP%"
mkdir "%BACKUP%\core" 2>nul

copy /Y "%FOXAI_ROOT%\core\foxai_web.py" "%BACKUP%\core\foxai_web.py" >nul || goto :backup_failed
copy /Y "%PAYLOAD%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul || goto :apply_failed

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
"%PYTHON%" -I -B -S -m py_compile "%FOXAI_ROOT%\core\foxai_web.py"
if errorlevel 1 goto :compile_failed

mkdir "%FOXAI_ROOT%\Backups\KayockWriterCalmHome" 2>nul
> "%FOXAI_ROOT%\Backups\KayockWriterCalmHome\LATEST.txt" echo %BACKUP%

echo.
echo ============================================================
echo WRITER UPDATE APPLIED AND PYTHON SYNTAX VERIFIED
echo ============================================================
echo Backup: %BACKUP%
echo.
echo Restart FOXAI WebUI and click Kayock Writer.
echo The sidebar should show:
echo   Kayock Writer
echo   Poetry Studio
echo   Story Forge
echo   World Builder
echo   My Writing
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
