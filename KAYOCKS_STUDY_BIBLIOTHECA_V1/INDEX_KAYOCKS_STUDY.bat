@echo off
setlocal EnableExtensions
title Index Kayock's Study Bibliotheca

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "APP=%~dp0study_server.py"

if not exist "%FOXAI_ROOT%\Library" (
    echo ERROR: FOXAI Library was not found.
    pause
    exit /b 2
)
if not exist "%PYTHON%" (
    echo ERROR: Portable Desktop Python was not found.
    pause
    exit /b 3
)

echo This reads PDFs under:
echo   %FOXAI_ROOT%\Library
echo.
echo It writes only the Bibliotheca index and a receipt.
echo Original PDFs are not modified or deleted.
echo.

choice /C YN /N /M "Index or refresh the Bibliotheca now? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. Nothing changed.
    pause
    exit /b 0
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"

"%PYTHON%" -I -B -S "%APP%" --root "%FOXAI_ROOT%" --index-once
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
