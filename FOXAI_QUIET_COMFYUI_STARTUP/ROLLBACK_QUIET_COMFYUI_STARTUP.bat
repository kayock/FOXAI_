@echo off
setlocal EnableExtensions
title Roll Back FOXAI Quiet ComfyUI Startup

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "LATEST=%FOXAI_ROOT%\Backups\QuietComfyStartup\LATEST.txt"

if not exist "%LATEST%" (
    echo No recorded backup was found.
    pause
    exit /b 2
)

set /p "BACKUP="<"%LATEST%"
if not exist "%BACKUP%\START_FOXAI_WEB_WITH_COMFYUI.bat" (
    echo Backup unavailable:
    echo %BACKUP%
    pause
    exit /b 3
)

choice /C YN /N /M "Restore the previous launchers? [Y/N]: "
if errorlevel 2 exit /b 0

copy /Y "%BACKUP%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" "%FOXAI_ROOT%\START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat" >nul
copy /Y "%BACKUP%\START_FOXAI_WEB_WITH_COMFYUI.bat" "%FOXAI_ROOT%\START_FOXAI_WEB_WITH_COMFYUI.bat" >nul

if exist "%BACKUP%\System\PortableRuntime\start_comfyui_quiet.NEW" (
    del /Q "%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py" 2>nul
) else (
    copy /Y "%BACKUP%\System\PortableRuntime\start_comfyui_quiet.py" "%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py" >nul
)

echo Rollback completed.
pause
