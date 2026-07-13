@echo off
setlocal
title KayocktheOS SmartSearch Root Staging Cleanup Rollback
cd /d "%~dp0"

set "PYTHON="
if exist "%~dp0env\python\python.exe" set "PYTHON=%~dp0env\python\python.exe"
if not defined PYTHON if exist "%~dp0..\env\python\python.exe" set "PYTHON=%~dp0..\env\python\python.exe"

if not defined PYTHON (
    echo Could not locate FOXAI portable Python.
    pause
    exit /b 1
)

set /p "BACKUP=Paste the full SmartSearchRootStagingCleanup backup folder path: "
"%PYTHON%" -S -u "%~dp0tools\rollback_smartsearch_root_staging_cleanup.py" "%~dp0.." "%BACKUP%"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
