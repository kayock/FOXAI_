@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE="
if exist "Z:\Hanger Bay\Development\Python\python.exe" set "PYTHON_EXE=Z:\Hanger Bay\Development\Python\python.exe"
if not defined PYTHON_EXE where py >nul 2>nul && set "PYTHON_EXE=py -3"
if not defined PYTHON_EXE where python >nul 2>nul && set "PYTHON_EXE=python"
if not defined PYTHON_EXE (
  echo Python was not found. No installation was attempted.
  pause
  exit /b 1
)
%PYTHON_EXE% -m unittest discover -s tests -v
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo PREVIEW 8 TESTS PASSED.) else (echo PREVIEW 8 TESTS FAILED.)
pause
exit /b %RC%
