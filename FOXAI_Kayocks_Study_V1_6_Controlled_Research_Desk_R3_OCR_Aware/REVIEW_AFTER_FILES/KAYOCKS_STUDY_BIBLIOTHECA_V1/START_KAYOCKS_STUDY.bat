@echo off
setlocal EnableExtensions
title Kayock's Study - The Bibliotheca V1.6

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "APP=%~dp0study_server.py"

echo ==================================================================
echo KAYOCK'S STUDY - THE BIBLIOTHECA V1.6
echo Read. Research. Preserve. Discover.
echo ==================================================================
echo.
echo Library: %FOXAI_ROOT%\Library
echo Address: http://127.0.0.1:8777
echo Original PDFs remain unchanged.
echo Press Ctrl+C here to stop the Study.
echo.

if not exist "%FOXAI_ROOT%\Library" (
    echo ERROR: Extract this complete folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)
if not exist "%PYTHON%" (
    echo ERROR: FOXAI portable Desktop Python was not found:
    echo %PYTHON%
    pause
    exit /b 3
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"

"%PYTHON%" -I -B -S "%APP%" --root "%FOXAI_ROOT%" --port 8777 --open
set "RESULT=%ERRORLEVEL%"

echo.
echo Kayock's Study stopped with code %RESULT%.
pause
exit /b %RESULT%
