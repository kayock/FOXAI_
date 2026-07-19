@echo off
setlocal EnableExtensions
title FOXAI Necroscope Portable PDF Index V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0necroscope_pdf_index.py"

echo ================================================================
echo FOXAI NECROSCOPE PORTABLE PDF INDEX V1
echo ================================================================
echo.
echo This reads Eric's owned MasterBook/Necroscope PDFs and creates a
echo private searchable page index under:
echo.
echo   %FOXAI_ROOT%\Projects\NecroscopeCampaign\SourceIndexV1
echo.
echo SOURCE PDFs REMAIN READ-ONLY.
echo No network access or package installation is used.
echo FOXAI's main Python environment is not changed.
echo.
echo Six books total about 1,011 pages. Initial indexing may take
echo several minutes depending on the USB and PDF structure.
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
    echo ERROR: Extract this folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)
if not exist "%PYTHON%" (
    echo ERROR: Portable Desktop Python was not found:
    echo   %PYTHON%
    pause
    exit /b 3
)
if not exist "%SCRIPT%" (
    echo ERROR: Indexing script is missing.
    pause
    exit /b 4
)

choice /C YN /N /M "Build the private read-only Necroscope page index? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. No files changed.
    pause
    exit /b 0
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%"
set "RESULT=%ERRORLEVEL%"

echo.
if not "%RESULT%"=="0" (
    echo Indexer finished with error code %RESULT%.
)
pause
exit /b %RESULT%
