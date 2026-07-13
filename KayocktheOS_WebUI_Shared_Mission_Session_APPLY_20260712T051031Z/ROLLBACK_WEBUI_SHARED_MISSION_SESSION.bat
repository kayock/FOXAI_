@echo off
setlocal
title KayocktheOS WebUI Shared Mission Session Rollback
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

"%PYTHON%" -u "%~dp0tools\rollback_webui_shared_mission_session.py"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
