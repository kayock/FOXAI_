@echo off
setlocal
title KayocktheOS Portable Python Fix Preview
cd /d "%~dp0"

set "PYTHON="
if exist "%~dp0env\python\python.exe" set "PYTHON=%~dp0env\python\python.exe"
if not defined PYTHON if exist "%~dp0..\env\python\python.exe" set "PYTHON=%~dp0..\env\python\python.exe"

if defined PYTHON (
    "%PYTHON%" "%~dp0tools\preview_portable_fix.py"
) else (
    py -3 "%~dp0tools\preview_portable_fix.py"
)

echo.
echo Preview only. No FOXAI file was modified.
pause
