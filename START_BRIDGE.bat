@echo off
setlocal
title FOXAI Command Bridge

cd /d "%~dp0"

echo ==========================================
echo FOXAI Command Bridge - Orion v9.0
echo ==========================================
echo.
echo Opening BridgeUI\foxai-command-bridge.html
echo.
start "" "%~dp0BridgeUI\foxai-command-bridge.html"
