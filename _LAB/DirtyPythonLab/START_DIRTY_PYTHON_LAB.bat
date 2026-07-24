@echo off
setlocal
cd /d "%~dp0"
title FOXAI Dirty Python Lab

set "PYTHON_EXE=Z:\Hanger Bay\Development\Python\python.exe"

if not exist "%PYTHON_EXE%" (
    echo.
    echo  FOXAI DIRTY PYTHON LAB
    echo  ----------------------
    echo  The known Hanger Bay Python was not found:
    echo  %PYTHON_EXE%
    echo.
    echo  Nothing was installed or changed.
    echo.
    pause
    exit /b 1
)

if not exist "Z:\FOXAI\_LAB\DirtyPythonLab" mkdir "Z:\FOXAI\_LAB\DirtyPythonLab"

"%PYTHON_EXE%" "%~dp0dirty_python_lab.py"

if errorlevel 1 (
    echo.
    echo  Dirty Python Lab stopped with an error.
    echo  Review the message above. No installer was run.
    echo.
    pause
)
endlocal
