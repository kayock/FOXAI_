@echo off
setlocal EnableExtensions
title FOXAI ComfyUI Operations Quick Panel

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo ============================================================
echo FOXAI ComfyUI Operations Quick Panel
echo ============================================================
echo Target: %FOXAI_ROOT%
echo.
echo This patch:
echo - adds a read-only expandable ComfyUI Operations viewer
echo - updates Desktop and WebUI
echo - keeps the two-window desktop launcher
echo - installs nothing and uses no network
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
    echo ERROR: This package must be extracted directly inside the FOXAI root.
    echo Expected: %FOXAI_ROOT%\foxai.py
    pause
    exit /b 2
)

if not exist "%FOXAI_ROOT%\ui\main_window.py" (
    echo ERROR: Missing live Desktop file.
    pause
    exit /b 3
)

if not exist "%FOXAI_ROOT%\core\foxai_web.py" (
    echo ERROR: Missing live WebUI file.
    pause
    exit /b 4
)

if not exist "%PYTHON%" (
    echo ERROR: Portable Python was not found.
    pause
    exit /b 5
)

echo Close FOXAI Desktop, WebUI, and ComfyUI before continuing.
choice /C YN /N /M "Continue with the small backed-up patch? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('"%PYTHON%" -I -B -S -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%dT%%H%%M%%S'))"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\ComfyOpsQuickPanel\%STAMP%"
mkdir "%BACKUP%\ui" 2>nul
mkdir "%BACKUP%\core" 2>nul
mkdir "%BACKUP%\System\PortableRuntime" 2>nul

copy /Y "%FOXAI_ROOT%\ui\main_window.py" "%BACKUP%\ui\main_window.py" >nul || goto :backup_failed
copy /Y "%FOXAI_ROOT%\core\foxai_web.py" "%BACKUP%\core\foxai_web.py" >nul || goto :backup_failed

if exist "%FOXAI_ROOT%\core\comfy_ops_monitor.py" (
    copy /Y "%FOXAI_ROOT%\core\comfy_ops_monitor.py" "%BACKUP%\core\comfy_ops_monitor.py" >nul
) else (
    type nul > "%BACKUP%\core\comfy_ops_monitor.NEW"
)

if exist "%FOXAI_ROOT%\System\PortableRuntime\comfy_console_tee.py" (
    copy /Y "%FOXAI_ROOT%\System\PortableRuntime\comfy_console_tee.py" "%BACKUP%\System\PortableRuntime\comfy_console_tee.py" >nul
) else (
    type nul > "%BACKUP%\System\PortableRuntime\comfy_console_tee.NEW"
)

if exist "%FOXAI_ROOT%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" (
    copy /Y "%FOXAI_ROOT%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" "%BACKUP%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" >nul
) else (
    type nul > "%BACKUP%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.NEW"
)

copy /Y "%PAYLOAD%\ui\main_window.py" "%FOXAI_ROOT%\ui\main_window.py" >nul || goto :apply_failed
copy /Y "%PAYLOAD%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul || goto :apply_failed
copy /Y "%PAYLOAD%\core\comfy_ops_monitor.py" "%FOXAI_ROOT%\core\comfy_ops_monitor.py" >nul || goto :apply_failed
copy /Y "%PAYLOAD%\System\PortableRuntime\comfy_console_tee.py" "%FOXAI_ROOT%\System\PortableRuntime\comfy_console_tee.py" >nul || goto :apply_failed
copy /Y "%PAYLOAD%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" "%FOXAI_ROOT%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" >nul || goto :apply_failed

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
"%PYTHON%" -I -B -S -m py_compile ^
  "%FOXAI_ROOT%\ui\main_window.py" ^
  "%FOXAI_ROOT%\core\foxai_web.py" ^
  "%FOXAI_ROOT%\core\comfy_ops_monitor.py" ^
  "%FOXAI_ROOT%\System\PortableRuntime\comfy_console_tee.py"
if errorlevel 1 goto :compile_failed

mkdir "%FOXAI_ROOT%\Backups\ComfyOpsQuickPanel" 2>nul
> "%FOXAI_ROOT%\Backups\ComfyOpsQuickPanel\LATEST.txt" echo %BACKUP%

echo.
echo ============================================================
echo PATCH APPLIED AND PYTHON SYNTAX VERIFIED
echo ============================================================
echo Backup: %BACKUP%
echo.
echo Start FOXAI with your existing Desktop or WebUI shortcut.
echo Desktop: click "COMFYUI OPERATIONS" in the sidebar.
echo WebUI: expand the green panel at the lower-right.
echo.
pause
exit /b 0

:backup_failed
echo ERROR: Backup failed. No patch was applied.
pause
exit /b 10

:apply_failed
echo ERROR: A file copy failed. Restoring the backup...
goto :rollback

:compile_failed
echo ERROR: Python syntax verification failed. Restoring the backup...
goto :rollback

:rollback
copy /Y "%BACKUP%\ui\main_window.py" "%FOXAI_ROOT%\ui\main_window.py" >nul
copy /Y "%BACKUP%\core\foxai_web.py" "%FOXAI_ROOT%\core\foxai_web.py" >nul

if exist "%BACKUP%\core\comfy_ops_monitor.NEW" (
    del /Q "%FOXAI_ROOT%\core\comfy_ops_monitor.py" 2>nul
) else (
    copy /Y "%BACKUP%\core\comfy_ops_monitor.py" "%FOXAI_ROOT%\core\comfy_ops_monitor.py" >nul
)

if exist "%BACKUP%\System\PortableRuntime\comfy_console_tee.NEW" (
    del /Q "%FOXAI_ROOT%\System\PortableRuntime\comfy_console_tee.py" 2>nul
) else (
    copy /Y "%BACKUP%\System\PortableRuntime\comfy_console_tee.py" "%FOXAI_ROOT%\System\PortableRuntime\comfy_console_tee.py" >nul
)

if exist "%BACKUP%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.NEW" (
    del /Q "%FOXAI_ROOT%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" 2>nul
) else (
    copy /Y "%BACKUP%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" "%FOXAI_ROOT%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" >nul
)

echo Rollback completed.
pause
exit /b 11
