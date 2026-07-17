@echo off
setlocal
title FOXAI Portable Runtime Phase 2A - Read-Only Probe
cd /d "%~dp0"

set "FOXAI_ROOT=%~dp0.."
set "PYTHON=%FOXAI_ROOT%\env\python\python.exe"

echo ================================================================
echo FOXAI PORTABLE RUNTIME PHASE 2A - READ-ONLY PROBE
echo ================================================================
echo.
echo This probe installs nothing and changes no launcher or config.
echo It writes only a timestamped report under Reports\PortableRuntimeProbe.
echo.

if not exist "%PYTHON%" (
    echo [STOPPED] Bundled Python was not found:
    echo %PYTHON%
    echo.
    pause
    exit /b 2
)

"%PYTHON%" -s "%~dp0portable_runtime_probe.py"
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" (
    echo [STOPPED] Probe returned error code %RESULT%.
) else (
    echo [COMPLETE] Read-only probe finished.
)
echo.
pause
exit /b %RESULT%
