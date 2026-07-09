@echo off
setlocal
title FOXAI CM v3.2 Capability Gap Analyzer

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v3.2 Capability Gap Analyzer
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_CAPABILITY_GAP_ANALYZER.py
) else (
    python TEST_CAPABILITY_GAP_ANALYZER.py
)

echo.
pause
