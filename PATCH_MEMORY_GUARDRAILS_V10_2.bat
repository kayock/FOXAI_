@echo off
setlocal
title FOXAI v10.2 Structured Memory Guardrails

cd /d "%~dp0"

echo ==========================================
echo FOXAI v10.2 Structured Memory Guardrails
echo ==========================================
echo.
echo This patches:
echo core_v10\memory_engine.py
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_MEMORY_GUARDRAILS_V10_2.py
) else (
    python PATCH_MEMORY_GUARDRAILS_V10_2.py
)

echo.
pause
