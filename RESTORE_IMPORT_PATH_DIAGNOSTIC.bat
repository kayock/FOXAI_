@echo off
setlocal
title FOXAI Restore Import Path Diagnostic

cd /d "%~dp0"

echo ==========================================
echo FOXAI Restore Import Path Diagnostic
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" RESTORE_IMPORT_PATH_DIAGNOSTIC.py
) else (
    python RESTORE_IMPORT_PATH_DIAGNOSTIC.py
)

echo.
pause
