@echo off
setlocal
title FOXAI Import Path Diagnostic

cd /d "%~dp0"

echo ==========================================
echo FOXAI Import Path Diagnostic
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" RUN_IMPORT_PATH_DIAGNOSTIC.py
) else (
    python RUN_IMPORT_PATH_DIAGNOSTIC.py
)

echo.
pause
