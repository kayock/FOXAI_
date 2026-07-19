@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "FOLDER=%FOXAI_ROOT%\Projects\NecroscopeCampaign\RulesPacketsV1"

if not exist "%FOLDER%" (
    echo Rules packet folder does not exist yet.
    echo Run RUN_NECROSCOPE_RULES_PACKET_EXPORTER.bat first.
    pause
    exit /b 2
)

start "" "%FOLDER%"
