@echo off
setlocal
title KayocktheOS Engineer Intake Repair Apply
cd /d "%~dp0"

set "PYTHON="
if exist "%~dp0env\python\python.exe" set "PYTHON=%~dp0env\python\python.exe"
if not defined PYTHON if exist "%~dp0..\env\python\python.exe" set "PYTHON=%~dp0..\env\python\python.exe"

if not defined PYTHON (
    echo Could not locate FOXAI portable Python.
    echo Expected env\python\python.exe in this folder or its parent.
    pause
    exit /b 1
)

"%PYTHON%" -u "%~dp0tools\apply_engineer_intake.py"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
    echo Engineer intake repair verified.
) else (
    echo The repair was cancelled, blocked, failed, or rolled back.
)
pause
exit /b %RC%
