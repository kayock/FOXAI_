@echo off
setlocal
title FOXAI Bridge Feed UI Install

cd /d "%~dp0"

echo ==========================================
echo FOXAI Bridge Feed UI Install
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

copy /Y "BridgeUI\foxai-bridge-feed.js" "Z:\FOXAI\BridgeUI\foxai-bridge-feed.js"
copy /Y "BridgeUI\foxai-bridge-feed.html" "Z:\FOXAI\BridgeUI\foxai-bridge-feed.html"

echo.
echo Installed Bridge Feed UI files.
echo.
pause
