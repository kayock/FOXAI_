@echo off
setlocal EnableExtensions
title Roll Back Bibliotheca V1.3

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0apply_bibliotheca_v1_3_recipe_heading_fix.py"

choice /C YN /N /M "Roll back V1.3 to Bibliotheca V1.2? [Y/N]: "
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
