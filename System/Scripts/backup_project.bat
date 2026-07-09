@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
if not exist "Backups" mkdir "Backups"
set STAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set STAMP=%STAMP: =0%
set OUT=Backups\KayocktheOS_backup_%STAMP%.zip
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '.\*' -DestinationPath '%OUT%' -Force"
echo Backup created: %OUT%
pause
