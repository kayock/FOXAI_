@echo off
setlocal EnableExtensions
title FOXAI Necroscope Campaign Room V1

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0necroscope_campaign_room.py"

echo ================================================================
echo FOXAI NECROSCOPE CAMPAIGN ROOM V1
echo ================================================================
echo.
echo Before playing:
echo   1. Start FOXAI WebUI.
echo   2. Start Fast Talk or Creative Brain in Artificial Minds.
echo   3. Keep the local chat engine running on 127.0.0.1:8080.
echo.
echo The Campaign Room will open at:
echo   http://127.0.0.1:8776
echo.
echo Source books and the private index remain READ-ONLY.
echo Campaign state is saved under:
echo   %FOXAI_ROOT%\Projects\NecroscopeCampaign\CampaignRoomV1
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
    echo ERROR: The Necroscope source index is missing.
    echo Run FOXAI_NECROSCOPE_PORTABLE_PDF_INDEX_V1 first.
    pause
    exit /b 4
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --port 8776
set "RESULT=%ERRORLEVEL%"

echo.
if not "%RESULT%"=="0" (
    echo Campaign Room ended with error code %RESULT%.
    pause
)
exit /b %RESULT%
