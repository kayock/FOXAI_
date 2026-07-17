@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "PYTHONNOUSERSITE=1"
set "PYTHONHOME=%~dp0Runtime\Desktop\python"
set "PYTHONPATH=%~dp0Runtime\Desktop\site-packages;%~dp0Runtime\Core\site-packages;%~dp0"
"%~dp0Runtime\Desktop\python\python.exe" -s "%~dp0foxai.py"
set "RC=%ERRORLEVEL%"
pause
exit /b %RC%
