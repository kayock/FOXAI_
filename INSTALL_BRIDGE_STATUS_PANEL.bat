@echo off
setlocal
title FOXAI Project Orion v7.2 Bridge Status Panel

cd /d "%~dp0"

echo ==========================================
echo FOXAI Project Orion v7.2 Bridge Status Panel
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
echo Installed:
echo Z:\FOXAI\BridgeUI\foxai-bridge-status.html
echo Z:\FOXAI\BridgeUI\foxai-bridge-status.css
echo Z:\FOXAI\BridgeUI\foxai-bridge-status.js
echo.
echo To test:
echo Open Z:\FOXAI\BridgeUI\DEMO_bridge_status.html
echo.
pause
