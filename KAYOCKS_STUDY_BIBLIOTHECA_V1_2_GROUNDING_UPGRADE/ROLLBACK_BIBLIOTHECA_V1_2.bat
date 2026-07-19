@echo off
setlocal EnableExtensions
title Roll Back Bibliotheca V1.2

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0apply_bibliotheca_v1_2_upgrade.py"

choice /C YN /N /M "Roll back V1.2 to Bibliotheca V1.1? [Y/N]: "
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
