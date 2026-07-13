@echo off
setlocal
title KayocktheOS SmartSearch Evidence Cleanup Preview
cd /d "%~dp0"

set "PYTHON="
if exist "%~dp0env\python\python.exe" set "PYTHON=%~dp0env\python\python.exe"
if not defined PYTHON if exist "%~dp0..\env\python\python.exe" set "PYTHON=%~dp0..\env\python\python.exe"

if not defined PYTHON (
    echo Could not locate FOXAI portable Python.
    echo Extract this preview folder directly inside Z:\FOXAI.
    pause
    exit /b 1
)

"%PYTHON%" -S -u "%~dp0tools\preview_smartsearch_evidence_cleanup.py"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
