@echo off
setlocal
title FOXAI Patch Conversation Shuttle Manifest
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" PATCH_CONVERSATION_MANIFEST_SERVICE_KIND.py
) else (
    python PATCH_CONVERSATION_MANIFEST_SERVICE_KIND.py
)

echo.
pause
