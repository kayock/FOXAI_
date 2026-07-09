@echo off
setlocal
title FOXAI Update Center Preview
cd /d "%~dp0"
echo ==========================================
echo FOXAI Update Center Preview
echo ==========================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" APPLY_UPDATE.py --preview
) else (
    python APPLY_UPDATE.py --preview
)
echo.
pause
