@echo off
setlocal EnableExtensions
title FOXAI Poem Selection Scope Fix

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "VERIFY=%~dp0verify_selection_scope_fix.py"

echo ============================================================
echo FOXAI POEM SELECTION SCOPE FIX
echo ============================================================
echo Changes only:
echo   core\foxai_web.py
echo.
echo Fixes workshop alternatives that return most or all of the
echo poem instead of only the selected stanza.
echo.
echo The workshop now:
echo - sends only two nearby context lines
echo - uses a compact Eric voice guide
echo - requires selection-sized answers
echo - rejects full-poem or oversized alternatives automatically
echo.
echo Do not use the oversized alternatives from the previous run.
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
choice /C YN /N /M "Apply this one-file backed-up scope fix? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('powershell.exe -NoLogo -NoProfile -NonInteractive -Command "Get-Date -Format yyyyMMddTHHmmss"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\PoemSelectionScopeFix\%STAMP%"
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

mkdir "%FOXAI_ROOT%\Backups\PoemSelectionScopeFix" 2>nul
> "%FOXAI_ROOT%\Backups\PoemSelectionScopeFix\LATEST.txt" echo %BACKUP%

echo.
echo ============================================================
echo POEM SELECTION SCOPE FIX APPLIED AND VERIFIED
echo ============================================================
echo Backup:
echo   %BACKUP%
echo.
echo Restart WebUI and repeat the selected-stanza test.
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
echo ERROR: Scope-fix verification failed. Restoring backup...
goto :rollback

:rollback
copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul
echo Rollback completed.
pause
exit /b 11
