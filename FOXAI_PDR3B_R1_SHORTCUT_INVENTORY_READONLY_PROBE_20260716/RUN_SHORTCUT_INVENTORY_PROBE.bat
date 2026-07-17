@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo FOXAI Portable Desktop Runtime Phase 3B-R1
echo Read-Only Shortcut Inventory and Resolution Probe
echo ============================================================
echo.
echo This probe does NOT edit shortcuts, launch FOXAI, install packages,
echo change launchers, or access the network.
echo.

where powershell.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: Windows PowerShell was not found.
    echo No probe was run and no FOXAI files were changed.
    pause
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0shortcut_inventory_probe.ps1" -BundleDir "%~dp0" %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo Probe complete. Open the newest folder inside probe_output.
) else (
    echo Probe stopped with exit code %RC%.
    echo Review the newest report inside probe_output if one was created.
)
echo.
pause
exit /b %RC%
