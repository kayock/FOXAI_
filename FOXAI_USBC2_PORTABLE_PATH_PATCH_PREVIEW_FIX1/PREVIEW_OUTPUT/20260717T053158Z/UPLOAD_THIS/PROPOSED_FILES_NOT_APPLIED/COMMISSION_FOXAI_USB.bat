@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI USB Commissioning

set "PY=%~dp0Runtime\Desktop\python\python.exe"
if not exist "%PY%" set "PY=%~dp0env\python\python.exe"
set "SCRIPT=%~dp0System\Commissioning\commission_usb.py"

if not exist "%PY%" (
  echo.
  echo NEEDS ATTENTION: commissioning Python is missing.
  echo Preferred: %~dp0Runtime\Desktop\python\python.exe
  echo Fallback:  %~dp0env\python\python.exe
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

set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONHOME="
set "PYTHONPATH=%~dp0Runtime\Desktop\site-packages;%~dp0Runtime\Core\site-packages"

"%PY%" -s "%SCRIPT%"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo FOXAI reported NEEDS ATTENTION. Review the commissioning report.
  pause
)

exit /b %RC%
