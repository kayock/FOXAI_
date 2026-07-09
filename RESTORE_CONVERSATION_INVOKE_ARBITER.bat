@echo off
setlocal
title FOXAI Restore Conversation Invoke Arbiter

cd /d "%~dp0"

echo ==========================================
echo FOXAI Restore Conversation Invoke Arbiter
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" RESTORE_CONVERSATION_INVOKE_ARBITER.py
) else (
    python RESTORE_CONVERSATION_INVOKE_ARBITER.py
)

echo.
pause
