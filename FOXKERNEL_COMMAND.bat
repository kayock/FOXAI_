@echo off
setlocal
title FOXAI Command OS v6.0 FOXKernel Command

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" FOXKERNEL_COMMAND.py %*
) else (
    python FOXKERNEL_COMMAND.py %*
)

echo.
pause
