@echo off
setlocal
title FOXAI Restore Academy Registrar

cd /d "%~dp0"

echo ==========================================
echo FOXAI Restore Academy Registrar
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" RESTORE_ACADEMY_REGISTRAR.py
) else (
    python RESTORE_ACADEMY_REGISTRAR.py
)

echo.
pause
