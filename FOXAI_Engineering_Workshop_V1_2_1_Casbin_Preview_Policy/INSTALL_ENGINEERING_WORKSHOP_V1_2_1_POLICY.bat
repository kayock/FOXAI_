@echo off
setlocal
cd /d "%~dp0"
set "PY=Z:\FOXAI\Runtime\Desktop\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0INSTALL_ENGINEERING_WORKSHOP_V1_2_1_POLICY.py" %*
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Installer failed with exit code %RC%.
pause
exit /b %RC%
