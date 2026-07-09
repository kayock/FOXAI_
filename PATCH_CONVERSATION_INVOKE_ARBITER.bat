@echo off
setlocal
title FOXAI CM v3.8 Conversation Invoke Arbiter

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v3.8 Conversation Invoke Arbiter
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" PATCH_CONVERSATION_INVOKE_ARBITER.py
) else (
    python PATCH_CONVERSATION_INVOKE_ARBITER.py
)

echo.
pause
