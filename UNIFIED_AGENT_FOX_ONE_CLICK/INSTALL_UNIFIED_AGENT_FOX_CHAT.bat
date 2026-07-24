@echo off
setlocal EnableExtensions
title FOXAI Unified Agent Fox Chat

set "FIXDIR=%~dp0"
for %%I in ("%FIXDIR%..") do set "FOXAI_ROOT=%%~fI"

set "TARGET=%FOXAI_ROOT%\core\director.py"
set "PATCH=%FIXDIR%director.py"
set "PY=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo.
echo FOXAI Unified Agent Fox Chat
echo ============================
echo.

if not exist "%PY%" (
    echo NOT INSTALLED
    echo Could not find FOXAI portable Python:
    echo %PY%
    echo.
    pause
    exit /b 2
)

"%PY%" -I -B -S "%FIXDIR%install_unified_agent_fox.py" "%FOXAI_ROOT%" "%TARGET%" "%PATCH%"
set "RESULT=%ERRORLEVEL%"

echo.
if "%RESULT%"=="0" (
    echo You may close this window and start FOXAI normally.
) else (
    echo Nothing else is required right now.
)
echo.
pause
exit /b %RESULT%
