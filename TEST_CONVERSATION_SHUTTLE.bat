@echo off
setlocal
title FOXAI CM v3.4 USS Conversation Shuttle Test
cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v3.4 USS Conversation Shuttle
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_CONVERSATION_SHUTTLE.py
) else (
    python TEST_CONVERSATION_SHUTTLE.py
)

echo.
pause
