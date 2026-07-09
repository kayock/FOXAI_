@echo off
setlocal
title FOXAI Project Orion v7.4 Bridge Live Captain's Log

cd /d "%~dp0"

echo ==========================================
echo FOXAI Project Orion v7.4 Bridge Live Log
echo ==========================================
echo.

if not exist "Z:\FOXAI" (
    echo ERROR: Z:\FOXAI not found.
    pause
    exit /b 1
)

if not exist "Z:\FOXAI\BridgeUI" (
    mkdir "Z:\FOXAI\BridgeUI"
)

xcopy /E /Y /I "BridgeUI" "Z:\FOXAI\BridgeUI"

echo.
echo Installed live Captain's Log bridge update.
echo.
echo Updated:
echo Z:\FOXAI\BridgeUI\foxai-bridge-status.js
echo Z:\FOXAI\BridgeUI\foxai-bridge-status.html
echo.
pause
