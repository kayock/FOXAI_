@echo off
setlocal
title FOXAI CM v2.4 USS Database Shuttle Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v2.4 USS Database Shuttle Test
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_VAULT_DATABASE_SHUTTLE.py
) else (
    python TEST_VAULT_DATABASE_SHUTTLE.py
)

echo.
pause
