@echo off
setlocal EnableExtensions
title FOXAI Repair Bay V1.2 Direct One-Line Fix

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0apply_repair_bay_v1_2_direct_fix.py"

echo ==================================================================
echo FOXAI REPAIR BAY V1.2 DIRECT ONE-LINE FIX
echo ==================================================================
echo.
echo Close FOXAI WebUI before running this patch.
echo.
echo This checks the exact broken live hash, changes one misplaced
echo JavaScript call, verifies the fixed hash, and creates a backup.
echo.
echo Target:
echo   %FOXAI_ROOT%\core\foxai_web.py
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
    echo ERROR: Extract this folder directly inside Z:\FOXAI.
    pause
    exit /b 2
)
if not exist "%PYTHON%" (
    echo ERROR: Portable Desktop Python was not found.
    pause
    exit /b 3
)

choice /C YN /N /M "Apply the direct Repair Bay V1.2 fix? [Y/N]: "
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
