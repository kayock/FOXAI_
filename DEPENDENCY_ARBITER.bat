@echo off
setlocal
title FOXAI CM v6.1 USS Dependency Arbiter
cd /d "%~dp0"
echo ==========================================
echo FOXAI CM v6.1 USS Dependency Arbiter
echo ==========================================
echo.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" DEPENDENCY_ARBITER.py
) else (
    python DEPENDENCY_ARBITER.py
)
echo.
pause
