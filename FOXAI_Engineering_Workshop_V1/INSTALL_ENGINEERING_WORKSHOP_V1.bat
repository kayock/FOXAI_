@echo off
setlocal
set "HERE=%~dp0"
set "PYTHON=Z:\FOXAI\Runtime\Desktop\python\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" "%HERE%INSTALL_ENGINEERING_WORKSHOP_V1.py" --foxai-root "Z:\FOXAI" %*
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
