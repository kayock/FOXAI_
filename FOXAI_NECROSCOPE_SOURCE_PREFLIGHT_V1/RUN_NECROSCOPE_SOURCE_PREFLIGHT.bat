@echo off
setlocal EnableExtensions
title FOXAI Necroscope Source Preflight V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0necroscope_source_preflight.py"

echo ================================================================
echo FOXAI NECROSCOPE SOURCE PREFLIGHT V1
echo ================================================================
echo.
echo READ-ONLY inspection of the owned PDFs under:
echo   %FOXAI_ROOT%\Library\DnD
echo.
echo It may create only:
echo   %FOXAI_ROOT%\Projects\NecroscopeCampaign\Preflight
echo.
echo It does not modify, rename, move, copy, or upload any source PDF.
echo It does not use the network.
echo.

if not exist "%FOXAI_ROOT%\foxai.py" (
  echo ERROR: Extract this folder directly inside Z:\FOXAI.
  pause
  exit /b 2
)
if not exist "%PYTHON%" (
  echo ERROR: Portable Desktop Python was not found.
  echo %PYTHON%
  pause
  exit /b 3
)
choice /C YN /N /M "Run the read-only Necroscope source inspection? [Y/N]: "
if errorlevel 2 exit /b 0
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
"%PYTHON%" -B "%SCRIPT%" --root "%FOXAI_ROOT%"
set "RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %RESULT%
