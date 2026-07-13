@echo off
setlocal
title KayocktheOS Portable Python Compatibility Rollback
cd /d "%~dp0"

set "PYTHON="
if exist "%~dp0env\python\python.exe" set "PYTHON=%~dp0env\python\python.exe"
if not defined PYTHON if exist "%~dp0..\env\python\python.exe" set "PYTHON=%~dp0..\env\python\python.exe"

if not defined PYTHON (
    echo Could not locate FOXAI portable Python.
    pause
    exit /b 1
)

"%PYTHON%" -u "%~dp0tools\rollback_portable_fix.py"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
