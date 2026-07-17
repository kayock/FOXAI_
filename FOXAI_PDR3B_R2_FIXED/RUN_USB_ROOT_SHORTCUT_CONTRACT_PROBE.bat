@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3B-R2-FIX1
echo USB-Root Shortcut Contract Evidence Probe
echo ============================================================
echo.
echo READ-ONLY DIAGNOSTIC:
echo - does not edit or create shortcuts
echo - does not launch FOXAI
echo - does not install packages
echo - does not change launchers or runtimes
echo - does not access the network
echo.

where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: Windows PowerShell was not found.
    echo No probe was run and no FOXAI files were changed.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0usb_root_shortcut_contract_probe.ps1" -BundleDir "%~dp0" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Probe complete.
    echo Open the newest folder inside probe_output and upload that folder as a ZIP.
) else (
    echo Probe stopped with exit code %RC%.
    echo Review the newest report inside probe_output if one was created.
)
echo.
pause
exit /b %RC%
