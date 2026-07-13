@echo off
setlocal
title KayocktheOS WebUI Shared Mission Session Apply
cd /d "%~dp0"

set "PYTHON="
if exist "%~dp0env\python\python.exe" set "PYTHON=%~dp0env\python\python.exe"
if not defined PYTHON if exist "%~dp0..\env\python\python.exe" set "PYTHON=%~dp0..\env\python\python.exe"

if not defined PYTHON (
    echo Could not locate FOXAI portable Python.
    echo Extract this bundle directly inside Z:\FOXAI.
    pause
    exit /b 1
)

"%PYTHON%" -u "%~dp0tools\apply_webui_shared_mission_session.py"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
    echo WebUI Shared Mission Session verified.
) else (
    echo The apply was cancelled, blocked, failed, or rolled back.
)
pause
exit /b %RC%
