@echo off
setlocal
title FOXAI Project Orion v7.1 Engineering Commissioning

cd /d "%~dp0"

echo ==========================================
echo FOXAI Project Orion v7.1
echo Engineering Department Commissioning
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" COMMISSION_ENGINEERING.py
) else (
    python COMMISSION_ENGINEERING.py
)

echo.
pause
