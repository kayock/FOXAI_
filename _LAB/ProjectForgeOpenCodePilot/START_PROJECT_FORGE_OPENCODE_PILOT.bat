@echo off
setlocal
cd /d "%~dp0"
title Project Forge - OpenCode Pilot
set "PYTHON=Z:\Hanger Bay\Development\Python\python.exe"
if not exist "%PYTHON%" (
  echo Hanger Bay Python was not found:
  echo %PYTHON%
  echo.
  pause
  exit /b 1
)
"%PYTHON%" "%~dp0forge_opencode_pilot.py"
set "EXITCODE=%ERRORLEVEL%"
echo.
echo Project Forge OpenCode Pilot stopped with exit code %EXITCODE%.
pause
exit /b %EXITCODE%
