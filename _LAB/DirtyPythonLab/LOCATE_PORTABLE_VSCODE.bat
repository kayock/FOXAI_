@echo off
setlocal
cd /d "%~dp0"
title FOXAI Dirty Python Lab - Locate Portable VS Code
set "PYTHON_EXE=Z:\Hanger Bay\Development\Python\python.exe"

if not exist "%PYTHON_EXE%" (
    echo.
    echo Hanger Bay Python was not found:
    echo %PYTHON_EXE%
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%~dp0dirty_python_lab.py" --locate-vscode
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
    echo The exact Code.exe path was verified and remembered by the lab.
) else (
    echo No verified Code.exe was found. Nothing was installed or changed.
)
echo.
pause
exit /b %RESULT%
