@echo off
setlocal EnableExtensions
title Roll Back Kayock's Study Integration V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0apply_kayocks_study_integration_v1.py"

choice /C YN /N /M "Roll back the main FOXAI Study integration? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. Nothing changed.
    pause
    exit /b 0
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"

"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --action rollback
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
