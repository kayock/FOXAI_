@echo off
setlocal
cd /d "%~dp0"
set "PYTHONNOUSERSITE=1"
"%~dp0env\python\python.exe" -s "%~dp0core\foxai_web.py"
pause
