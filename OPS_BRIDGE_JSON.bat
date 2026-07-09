@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" OPS_BRIDGE.py --json %*
) else (
    python OPS_BRIDGE.py --json %*
)
