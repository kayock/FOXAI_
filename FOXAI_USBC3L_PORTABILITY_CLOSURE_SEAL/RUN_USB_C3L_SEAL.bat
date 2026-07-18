@echo off
setlocal EnableExtensions
set "PACKAGE_DIR=%~dp0"
if "%PACKAGE_DIR:~-1%"=="\" set "PACKAGE_DIR=%PACKAGE_DIR:~0,-1%"
for %%I in ("%PACKAGE_DIR%\..") do set "ROOT=%%~fI"
set "PY=%ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_DIR%\System\Closure\usbc3l_portability_closure.py"
echo ================================================================
echo   FOXAI USB C3L - PORTABILITY CLOSURE AND KNOWN-GOOD SEAL
echo ================================================================
echo.
if not exist "%PY%" (
  echo [STOPPED] Portable Python is missing: %PY%
  pause
  exit /b 19
)
if not exist "%SCRIPT%" (
  echo [STOPPED] C3L script is missing: %SCRIPT%
  pause
  exit /b 19
)
"%PY%" -I -B -S "%SCRIPT%" --root "%ROOT%" --package "%PACKAGE_DIR%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [COMPLETE] C3L portability closure and known-good baseline seal succeeded.
) else (
  echo [STOPPED] C3L failed closed with exit code %RC%.
)
echo.
pause
exit /b %RC%
