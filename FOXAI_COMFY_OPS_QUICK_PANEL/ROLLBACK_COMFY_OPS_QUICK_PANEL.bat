@echo off
setlocal EnableExtensions
title Roll Back FOXAI ComfyUI Operations Quick Panel

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "LATEST=%FOXAI_ROOT%\Backups\ComfyOpsQuickPanel\LATEST.txt"

if not exist "%LATEST%" (
    echo No recorded quick-panel backup was found.
    pause
    exit /b 2
)

set /p "BACKUP="<"%LATEST%"
if not exist "%BACKUP%\ui\main_window.py" (
    echo The recorded backup is unavailable:
    echo %BACKUP%
    pause
    exit /b 3
)

echo Backup to restore:
echo %BACKUP%
choice /C YN /N /M "Restore it? [Y/N]: "
if errorlevel 2 (
    echo Cancelled.
    pause
    exit /b 0
)

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
