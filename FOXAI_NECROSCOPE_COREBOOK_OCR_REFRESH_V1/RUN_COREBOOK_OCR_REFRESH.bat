@echo off
setlocal EnableExtensions
title FOXAI Necroscope Corebook OCR Refresh V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0refresh_necroscope_corebook_ocr.py"

echo ==================================================================
echo FOXAI NECROSCOPE COREBOOK OCR REFRESH V1
echo ==================================================================
echo.
echo Expected OCR copy:
echo   %FOXAI_ROOT%\Library\DnD\Masterbook Corebook_OCR_searchable.pdf
echo.
echo Close the Necroscope Campaign Room before running this refresh.
echo.
echo This opens the OCR PDF read-only, backs up the private index,
echo replaces only the empty corebook rows, and exports exact rule pages.
echo No network access or package installation is used.
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
    echo ERROR: Extract this package directly inside Z:\FOXAI.
    pause
    exit /b 2
)
if not exist "%PYTHON%" (
    echo ERROR: Portable Desktop Python was not found.
    pause
    exit /b 3
)
if not exist "%FOXAI_ROOT%\Library\DnD\Masterbook Corebook_OCR_searchable.pdf" (
    echo ERROR: The OCR corebook was not found under Library\DnD.
    pause
    exit /b 4
)

choice /C YN /N /M "Refresh the private Necroscope index with the OCR corebook? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. Nothing changed.
    pause
    exit /b 0
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%"
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
