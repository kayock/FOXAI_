@echo off
setlocal
title FOXAI - Stop Chat Engine

echo ==========================================
echo FOXAI Stop Chat Engine
echo ==========================================
echo.
echo This will stop llama-server.exe if it is running.
echo.

tasklist /FI "IMAGENAME eq llama-server.exe" | find /I "llama-server.exe" >nul
if errorlevel 1 (
    echo No llama-server.exe process found.
    pause
    exit /b 0
)

echo Found llama-server.exe.
echo Stopping...
taskkill /F /IM llama-server.exe

echo.
echo Done.
pause
