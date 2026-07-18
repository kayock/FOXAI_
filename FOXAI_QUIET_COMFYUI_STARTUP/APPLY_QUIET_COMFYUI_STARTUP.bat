@echo off
setlocal EnableExtensions
title FOXAI Quiet ComfyUI Startup

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PAYLOAD=%~dp0payload"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo ============================================================
echo FOXAI QUIET COMFYUI STARTUP
echo ============================================================
echo Removes the green ComfyUI console from normal startup.
echo Progress still writes to a plain hidden log for FOXAI bars.
echo The fragile comfy_console_tee.py wrapper is no longer used.
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
    echo ERROR: Extract this folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)
if not exist "%PYTHON%" (
    echo ERROR: Portable Python was not found.
    pause
    exit /b 3
)

echo Close FOXAI Desktop, WebUI, and the green ComfyUI console.
choice /C YN /N /M "Apply the small backed-up launcher update? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

for /f %%T in ('"%PYTHON%" -I -B -S -c "from datetime import datetime; print(datetime.now().strftime('%%Y%%m%%dT%%H%%M%%S'))"') do set "STAMP=%%T"
if not defined STAMP set "STAMP=manual"

set "BACKUP=%FOXAI_ROOT%\Backups\QuietComfyStartup\%STAMP%"
mkdir "%BACKUP%\System\PortableRuntime" 2>nul

copy /Y "%FOXAI_ROOT%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" "%BACKUP%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" >nul || goto :backup_failed
copy /Y "%FOXAI_ROOT%\START_FOXAI_WEB_WITH_COMFYUI.bat" "%BACKUP%\START_FOXAI_WEB_WITH_COMFYUI.bat" >nul || goto :backup_failed

if exist "%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py" (
    copy /Y "%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py" "%BACKUP%\System\PortableRuntime\start_comfyui_quiet.py" >nul
) else (
    type nul > "%BACKUP%\System\PortableRuntime\start_comfyui_quiet.NEW"
)

copy /Y "%PAYLOAD%\System\PortableRuntime\start_comfyui_quiet.py" "%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py" >nul || goto :apply_failed
copy /Y "%PAYLOAD%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" "%FOXAI_ROOT%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" >nul || goto :apply_failed
copy /Y "%PAYLOAD%\START_FOXAI_WEB_WITH_COMFYUI.bat" "%FOXAI_ROOT%\START_FOXAI_WEB_WITH_COMFYUI.bat" >nul || goto :apply_failed

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
"%PYTHON%" -I -B -S -m py_compile "%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py"
if errorlevel 1 goto :compile_failed

mkdir "%FOXAI_ROOT%\Backups\QuietComfyStartup" 2>nul
> "%FOXAI_ROOT%\Backups\QuietComfyStartup\LATEST.txt" echo %BACKUP%

echo.
echo QUIET STARTUP APPLIED AND SYNTAX VERIFIED.
echo Backup: %BACKUP%
echo.
echo Your existing Desktop and WebUI shortcuts keep working.
echo They will no longer open the green ComfyUI console.
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
copy /Y "%BACKUP%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" "%FOXAI_ROOT%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" >nul
copy /Y "%BACKUP%\START_FOXAI_WEB_WITH_COMFYUI.bat" "%FOXAI_ROOT%\START_FOXAI_WEB_WITH_COMFYUI.bat" >nul

if exist "%BACKUP%\System\PortableRuntime\start_comfyui_quiet.NEW" (
    del /Q "%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py" 2>nul
) else (
    copy /Y "%BACKUP%\System\PortableRuntime\start_comfyui_quiet.py" "%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py" >nul
)

echo Rollback completed.
pause
exit /b 11
