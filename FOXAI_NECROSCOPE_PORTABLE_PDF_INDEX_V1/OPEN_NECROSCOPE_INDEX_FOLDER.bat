@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "FOLDER=%FOXAI_ROOT%\Projects\NecroscopeCampaign\SourceIndexV1"

if not exist "%FOLDER%" (
    echo The index output folder does not exist yet.
    echo Run RUN_NECROSCOPE_PDF_INDEX.bat first.
    pause
    exit /b 2
)

start "" "%FOLDER%"
