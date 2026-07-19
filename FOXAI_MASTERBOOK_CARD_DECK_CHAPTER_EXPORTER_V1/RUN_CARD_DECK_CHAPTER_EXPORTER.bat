@echo off
setlocal EnableExtensions
title FOXAI MasterBook Card Deck Chapter Exporter V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0export_masterbook_card_deck_chapter.py"

echo ==================================================================
echo FOXAI MASTERBOOK CARD DECK CHAPTER EXPORTER V1
echo ==================================================================
echo.
echo This performs a READ-ONLY export of PDF pages 118 through 135.
echo.
echo It checks whether the OCR corebook reached the live SQLite index.
echo If not, it reads the searchable OCR PDF directly.
echo.
echo It does not modify the PDF or database.
echo It does not use the network.
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

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%"
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
