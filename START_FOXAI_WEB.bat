@echo off
setlocal
title FOXAI Web Console v9
cd /d "%~dp0"
set "FOXAI_URL=http://127.0.0.1:8765"
set "KAYOCK_BROWSER=%~d0\Kayock-Browser-2.5.3-rc.1-Portable.exe"
echo ==========================================
echo FOXAI Web Console v9 - Mission Memory
echo ==========================================
echo.
echo Starting local dashboard: %FOXAI_URL%
echo.
if exist "%CD%\env\python\python.exe" (
    start "FOXAI Web Server" /min "%CD%\env\python\python.exe" "%CD%\core\foxai_web.py"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        start "FOXAI Web Server" /min py -3 "%CD%\core\foxai_web.py"
    ) else (
        start "FOXAI Web Server" /min python "%CD%\core\foxai_web.py"
    )
)
timeout /t 2 /nobreak >nul
if exist "%KAYOCK_BROWSER%" (
    start "Kayock Browser - FOXAI" "%KAYOCK_BROWSER%" "%FOXAI_URL%"
) else (
    start "" "%FOXAI_URL%"
)
echo.
echo FOXAI Web Console is running. If needed open: %FOXAI_URL%
pause
