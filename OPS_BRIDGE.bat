@echo off
setlocal
title FOXAI OPS Bridge

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" OPS_BRIDGE.py %*
) else (
    python OPS_BRIDGE.py %*
)
