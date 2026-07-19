@echo off
setlocal
cd /d "%~dp0"
set "PY=Z:\FOXAI\Runtime\Desktop\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0ROLLBACK_ENGINEERING_WORKSHOP_V1_2.py" %*
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
