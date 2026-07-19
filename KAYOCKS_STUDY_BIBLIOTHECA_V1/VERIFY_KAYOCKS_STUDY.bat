@echo off
setlocal EnableExtensions
title Verify Kayock's Study Bibliotheca

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "APP=%~dp0study_server.py"

if not exist "%PYTHON%" (
    echo ERROR: Portable Desktop Python was not found.
    pause
    exit /b 3
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"

"%PYTHON%" -I -B -S "%APP%" --root "%FOXAI_ROOT%" --verify
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
