@echo off
setlocal
title FOXAI Install USS Conversation Shuttle
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" INSTALL_CONVERSATION_SHUTTLE.py
) else (
    python INSTALL_CONVERSATION_SHUTTLE.py
)

echo.
pause
