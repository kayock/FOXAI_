@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI Safe GitHub Source Upload

set "SCRIPT=%~dp0System\GitHub\push_source_snapshot.ps1"

if not exist "%SCRIPT%" (
    echo ERROR: Safe GitHub uploader is missing:
    echo %SCRIPT%
    pause
    exit /b 2
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass ^
  -File "%SCRIPT%" -RepoRoot "%~dp0"

set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
    echo FOXAI source upload finished successfully.
) else (
    echo FOXAI source upload stopped with code %RC%.
    echo Review the message and report above. No runtime files were deleted.
)
echo.
pause
exit /b %RC%
