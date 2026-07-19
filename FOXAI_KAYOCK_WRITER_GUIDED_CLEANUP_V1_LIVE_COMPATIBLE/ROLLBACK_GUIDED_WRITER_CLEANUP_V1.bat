@echo off
setlocal EnableExtensions
title Roll Back FOXAI Guided Writer Cleanup V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0apply_guided_writer_cleanup_v1.py"

echo ================================================================
echo ROLL BACK KAYOCK WRITER GUIDED CLEANUP V1
echo ================================================================
echo.
echo This works only while the live file still matches Guided V1.
echo A copy of Guided V1 is preserved before restoring the backup.
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
