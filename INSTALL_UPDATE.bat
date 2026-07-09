@echo off
setlocal
title FOXAI Update Center Apply
cd /d "%~dp0"
echo ==========================================
echo FOXAI Update Center Apply
echo ==========================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" APPLY_UPDATE.py
) else (
    python APPLY_UPDATE.py
)
echo.
pause
