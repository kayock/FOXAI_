@echo off
setlocal
title FOXAI CM v6.3 USS Academy Registrar Patch

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v6.3 USS Academy Registrar
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" PATCH_ACADEMY_REGISTRAR.py
) else (
    python PATCH_ACADEMY_REGISTRAR.py
)

echo.
pause
