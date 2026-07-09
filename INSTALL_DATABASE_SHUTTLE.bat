@echo off
setlocal
title FOXAI Install USS Database Shuttle

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" INSTALL_DATABASE_SHUTTLE.py
) else (
    python INSTALL_DATABASE_SHUTTLE.py
)

echo.
pause
