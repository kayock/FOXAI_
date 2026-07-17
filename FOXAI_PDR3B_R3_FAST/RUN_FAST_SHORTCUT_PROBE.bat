@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3B-R3 FAST
echo Narrow Shortcut Contract Probe
echo ============================================================
echo.
echo READ-ONLY DIAGNOSTIC:
echo - checks only a few known folders
echo - does not scan the full USB or computer
echo - does not edit or create shortcuts
echo - does not launch FOXAI
echo - does not install packages
echo - does not access the network
echo.

where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: Windows PowerShell was not found.
    echo Nothing was changed.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0shortcut_probe_fast.ps1" -BundleDir "%~dp0" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Fast probe complete.
    echo Zip the newest folder inside probe_output and upload it.
) else (
    echo Probe stopped with exit code %RC%.
    echo Nothing was intentionally changed.
)
echo.
pause
exit /b %RC%
