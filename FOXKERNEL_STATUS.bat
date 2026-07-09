@echo off
setlocal
title FOXAI Command OS v6.0 FOXKernel Status

cd /d "%~dp0"

echo ==========================================
echo FOXAI Command OS v6.0 FOXKernel Status
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" FOXKERNEL_STATUS.py
) else (
    python FOXKERNEL_STATUS.py
)

echo.
pause
