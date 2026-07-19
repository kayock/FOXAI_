@echo off
setlocal EnableExtensions
title FOXAI - Kayock's Study Integration V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0apply_kayocks_study_integration_v1.py"

echo ==================================================================
echo FOXAI - KAYOCK'S STUDY INTEGRATION V1
echo ==================================================================
echo.
echo Close the FOXAI WebUI and its command window before continuing.
echo.
echo This integration:
echo   - changes only core\foxai_web.py
echo   - preserves the Bibliotheca database and creates a snapshot
echo   - leaves Writer, Repair Bay, and navigation grouping untouched
echo   - leaves the standalone Study untouched
echo.

if not exist "%FOXAI_ROOT%\core\foxai_web.py" (
    echo ERROR: Extract this complete folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)
if not exist "%PYTHON%" (
    echo ERROR: FOXAI portable Desktop Python was not found.
    pause
    exit /b 3
)

choice /C YN /N /M "Apply Kayock's Study Integration V1? [Y/N]: "
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
