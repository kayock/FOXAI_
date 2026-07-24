@echo off
setlocal
cd /d "%~dp0"
title FOXAI Dirty Python Lab - Live Acceptance Check
set "PYTHON_EXE=Z:\Hanger Bay\Development\Python\python.exe"

if not exist "%PYTHON_EXE%" (
    echo.
    echo Hanger Bay Python was not found:
    echo %PYTHON_EXE%
    echo.
    pause
    exit /b 1
)

echo.
echo FOXAI DIRTY PYTHON LAB - LIVE ACCEPTANCE CHECK
echo ------------------------------------------------
echo This will ask the shared Qwen endpoint for one harmless print script,
echo save it in a disposable run folder, execute it, and show the result.
echo.

"%PYTHON_EXE%" "%~dp0dirty_python_lab.py" --acceptance-test
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" (
    echo LIVE MACHINE ACCEPTANCE PASSED.
) else (
    echo LIVE MACHINE ACCEPTANCE DID NOT PASS.
    echo Exact evidence was saved in the newest runs folder.
)
echo.
pause
exit /b %RESULT%
