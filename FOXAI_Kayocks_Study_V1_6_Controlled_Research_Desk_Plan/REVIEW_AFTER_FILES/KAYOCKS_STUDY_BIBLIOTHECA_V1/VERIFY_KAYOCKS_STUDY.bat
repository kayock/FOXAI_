@echo off
setlocal EnableExtensions
title Verify Kayock's Study Bibliotheca V1.6

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "APP=%~dp0study_server.py"
set "V16=%~dp0VERIFY_KAYOCKS_STUDY_V1_6.py"

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
if errorlevel 1 goto :failed
"%PYTHON%" -I -B -S "%V16%" --root "%FOXAI_ROOT%"
if errorlevel 1 goto :failed

echo.
echo Kayock's Study V1.6 verification passed.
pause
exit /b 0

:failed
echo.
echo Kayock's Study V1.6 verification failed.
pause
exit /b 4
