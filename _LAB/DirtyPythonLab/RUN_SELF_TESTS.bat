@echo off
setlocal
cd /d "%~dp0"
title FOXAI Dirty Python Lab - Self Tests
set "PYTHON_EXE=Z:\Hanger Bay\Development\Python\python.exe"
if not exist "%PYTHON_EXE%" (
    echo Hanger Bay Python not found: %PYTHON_EXE%
    pause
    exit /b 1
)
"%PYTHON_EXE%" -m unittest discover -s tests -v
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
    echo ALL DIRTY PYTHON LAB TESTS PASSED.
) else (
    echo ONE OR MORE TESTS FAILED. No files were installed or changed outside the test temp folder.
)
echo.
pause
exit /b %RESULT%
