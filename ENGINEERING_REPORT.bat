@echo off
setlocal
title FOXAI Engineering Report

cd /d "%~dp0"

echo ==========================================
echo FOXAI Engineering Report
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" ENGINEERING_REPORT.py
) else (
    python ENGINEERING_REPORT.py
)

echo.
pause
