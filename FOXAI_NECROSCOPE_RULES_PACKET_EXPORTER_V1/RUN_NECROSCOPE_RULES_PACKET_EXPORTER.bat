@echo off
setlocal EnableExtensions
title FOXAI Necroscope Rules Packet Exporter V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0export_necroscope_rules_packets.py"

echo ================================================================
echo FOXAI NECROSCOPE RULES PACKET EXPORTER V1
echo ================================================================
echo.
echo This reads the private SQLite page index and creates compact,
echo page-cited campaign preparation packets under:
echo.
echo   %FOXAI_ROOT%\Projects\NecroscopeCampaign\RulesPacketsV1
echo.
echo It does not modify the source PDFs or the source index.
echo It does not use the network.
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
if not exist "%FOXAI_ROOT%\Projects\NecroscopeCampaign\SourceIndexV1\necroscope_sources.sqlite3" (
    echo ERROR: The Necroscope source index has not been built.
    pause
    exit /b 4
)

choice /C YN /N /M "Export the private page-cited rules packets? [Y/N]: "
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
    echo Exporter finished with error code %RESULT%.
)
pause
exit /b %RESULT%
