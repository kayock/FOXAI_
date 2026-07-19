@echo off
setlocal EnableExtensions
for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "FOLDER=%FOXAI_ROOT%\Projects\NecroscopeCampaign\CampaignRoomV1"
if not exist "%FOLDER%" mkdir "%FOLDER%"
start "" "%FOLDER%"
