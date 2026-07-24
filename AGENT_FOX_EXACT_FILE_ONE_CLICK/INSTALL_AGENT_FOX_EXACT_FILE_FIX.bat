@echo off
setlocal EnableExtensions
title FOXAI Agent Fox Exact File Fix

set "FIXDIR=%~dp0"
for %%I in ("%FIXDIR%..") do set "FOXAI_ROOT=%%~fI"

set "TARGET=%FOXAI_ROOT%\System\AgentFoxTechnicalCore\desktop_self_knowledge_integration_v1.py"
set "REPLACEMENT=%FIXDIR%desktop_self_knowledge_integration_v1.py"
set "PY=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"

echo.
echo FOXAI Agent Fox Exact File Fix
echo ==============================
echo.

if not exist "%PY%" (
    echo NOT INSTALLED
    echo Could not find FOXAI portable Python:
    echo %PY%
    echo.
    pause
    exit /b 2
)

"%PY%" -I -B -S "%FIXDIR%install_agent_fox_exact_file.py" "%FOXAI_ROOT%" "%TARGET%" "%REPLACEMENT%"
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
