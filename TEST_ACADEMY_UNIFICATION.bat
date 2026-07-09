@echo off
setlocal
title FOXAI Project Orion v8.2 Academy Unification Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI Project Orion v8.2 Academy Unification
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_ACADEMY_UNIFICATION.py
) else (
    python TEST_ACADEMY_UNIFICATION.py
)

echo.
pause
