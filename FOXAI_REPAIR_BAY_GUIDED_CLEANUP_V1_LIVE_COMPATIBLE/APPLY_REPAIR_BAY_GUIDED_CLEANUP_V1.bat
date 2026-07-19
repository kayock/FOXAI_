@echo off
setlocal EnableExtensions
title FOXAI Repair Bay Guided Cleanup V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0apply_repair_bay_guided_cleanup_v1.py"

echo ==================================================================
echo FOXAI REPAIR BAY GUIDED CLEANUP V1
echo ==================================================================
echo.
echo Close FOXAI WebUI before applying this exact-hash update.
echo.
echo This changes only:
echo   %FOXAI_ROOT%\core\foxai_web.py
echo.
echo It creates a verified timestamped backup and receipt.
echo It does not alter repair records, projects, models, PDFs, or runtimes.
echo It does not use the network.
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

choice /C YN /N /M "Apply Repair Bay Guided Cleanup V1? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. Nothing changed.
    pause
    exit /b 0
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --action apply
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
