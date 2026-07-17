@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI USB Commissioning

set "PY=%~dp0env\python\python.exe"
set "SCRIPT=%~dp0System\Commissioning\commission_usb.py"

if not exist "%PY%" (
  echo.
  echo NEEDS ATTENTION: bundled Python is missing.
  echo Expected: %PY%
  echo No installation or repair was attempted.
  echo.
  pause
  exit /b 2
)

if not exist "%SCRIPT%" (
  echo.
  echo NEEDS ATTENTION: commissioning script is missing.
  echo Expected: %SCRIPT%
  echo.
  pause
  exit /b 2
)

"%PY%" "%SCRIPT%"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo FOXAI reported NEEDS ATTENTION. Review the commissioning report.
  pause
)

exit /b %RC%
