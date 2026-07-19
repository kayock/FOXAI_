@echo off
setlocal EnableExtensions
title Roll Back FOXAI Repair Bay Guided Cleanup V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0apply_repair_bay_guided_cleanup_v1.py"

echo ==================================================================
echo ROLL BACK REPAIR BAY GUIDED CLEANUP V1
echo ==================================================================
echo.
echo This rollback runs only while the live WebUI still matches Guided V1.
echo A copy of Guided V1 is preserved before the old version is restored.
echo.

choice /C YN /N /M "Restore the reviewed pre-cleanup WebUI? [Y/N]: "
if errorlevel 2 (
    echo Cancelled. Nothing changed.
    pause
    exit /b 0
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --action rollback
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
