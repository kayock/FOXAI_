@echo off
setlocal
title FOXAI CM v3.4a Fleet Synchronization Test
cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v3.4a Fleet Synchronization Test
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" TEST_FLEET_SYNC_CONVERSATION.py
) else (
    python TEST_FLEET_SYNC_CONVERSATION.py
)

echo.
pause
