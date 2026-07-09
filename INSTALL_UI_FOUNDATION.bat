@echo off
setlocal
title FOXAI Install Mission Control UI Foundation

cd /d "%~dp0"

echo ==========================================
echo FOXAI Mission Control UI Foundation
echo Installing Rich + Textual into .venv
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m pip install -r requirements-ui.txt
) else (
    python -m pip install -r requirements-ui.txt
)

echo.
pause
