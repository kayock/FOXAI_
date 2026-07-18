@echo off
setlocal EnableExtensions
set "PACKAGE_DIR=%~dp0"
if "%PACKAGE_DIR:~-1%"=="\" set "PACKAGE_DIR=%PACKAGE_DIR:~0,-1%"
for %%I in ("%PACKAGE_DIR%\..") do set "ROOT=%%~fI"
set "PY=%ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_DIR%\System\Airlock\usbc4a_custom_node_airlock_preflight.py"
echo ================================================================
echo   FOXAI USB C4A - CUSTOM NODE AIRLOCK STATIC PREFLIGHT
echo ================================================================
echo.
if not exist "%PY%" (echo [STOPPED] Portable Python missing: %PY%&pause&exit /b 19)
if not exist "%SCRIPT%" (echo [STOPPED] C4A script missing: %SCRIPT%&pause&exit /b 19)
"%PY%" -I -B -S "%SCRIPT%" --root "%ROOT%" --package "%PACKAGE_DIR%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo [COMPLETE] C4A static Custom Node Airlock preflight finished.) else (echo [STOPPED] C4A failed closed with exit code %RC%.)
echo.
pause
exit /b %RC%
