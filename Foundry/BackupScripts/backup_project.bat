@echo off
title KayocktheOS Backup
cd /d "%~dp0..\.."
where python >nul 2>nul
if %errorlevel%==0 (
    python Foundry\BackupScriptsackup_project.py
) else (
    py Foundry\BackupScriptsackup_project.py
)
pause
