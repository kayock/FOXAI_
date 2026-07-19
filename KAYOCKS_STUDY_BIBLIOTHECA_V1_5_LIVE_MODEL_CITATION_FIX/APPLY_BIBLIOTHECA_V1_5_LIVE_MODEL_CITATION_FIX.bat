@echo off
setlocal EnableExtensions
title Kayock's Study - Bibliotheca V1.5

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0apply_bibliotheca_v1_5_live_model_citation_fix.py"

echo ==================================================================
echo KAYOCK'S STUDY - THE BIBLIOTHECA V1.5
echo LIVE MODEL STATUS AND EXACT CITATION LABELS
echo ==================================================================
echo.
echo Close Kayock's Study and its black command window before continuing.
echo.
echo This patch:
echo   - preserves and snapshots the Bibliotheca database
echo   - replaces only study_server.py
echo   - updates the model badge automatically without a page refresh
echo   - replaces safe citation placeholders with exact source labels
echo   - uses localhost only
echo.

if not exist "%FOXAI_ROOT%\Library" (
    echo ERROR: Extract this folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)
if not exist "%PYTHON%" (
    echo ERROR: FOXAI portable Desktop Python was not found.
    pause
    exit /b 3
)

choice /C YN /N /M "Apply Bibliotheca V1.5? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. Nothing changed.
    pause
    exit /b 0
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"

"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --action apply
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
