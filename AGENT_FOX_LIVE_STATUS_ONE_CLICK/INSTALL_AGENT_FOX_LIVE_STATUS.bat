@echo off
setlocal EnableExtensions
title FOXAI Agent Fox Live Status

set "FIXDIR=%~dp0"
for %%I in ("%FIXDIR%..") do set "FOXAI_ROOT=%%~fI"

set "TARGET=%FOXAI_ROOT%\core\foxai_web.py"
set "REPLACEMENT=%FIXDIR%foxai_web.py"
set "PY=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo.
echo FOXAI Agent Fox Live Status
echo ===========================
echo.

if not exist "%PY%" (
    echo NOT INSTALLED
    echo Could not find FOXAI portable Python:
    echo %PY%
    echo.
    pause
    exit /b 2
)

"%PY%" -I -B -S "%FIXDIR%install_agent_fox_live_status.py" "%FOXAI_ROOT%" "%TARGET%" "%REPLACEMENT%"
set "RESULT=%ERRORLEVEL%"

echo.
if "%RESULT%"=="0" (
    echo You may close this window and start FOXAI WebUI normally.
) else (
    echo Nothing else is required right now.
)
echo.
pause
exit /b %RESULT%
