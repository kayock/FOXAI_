@echo off
setlocal EnableExtensions
for %%I in ("%~dp0.") do set "PACKAGE_DIR=%%~fI"
for %%I in ("%PACKAGE_DIR%\..") do set "ROOT=%%~fI"
set "PY=%ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_DIR%\System\Closure\usbc4f_dual_profile_closure.py"
echo ================================================================
echo   FOXAI USB C4F - DUAL-PROFILE BASELINE SEAL AND C4 CLOSURE
echo ================================================================
echo.
if not exist "%PY%" (
  echo [STOPPED] Portable Python is missing: %PY%
  pause
  exit /b 19
)
if not exist "%SCRIPT%" (
  echo [STOPPED] C4F closure script is missing: %SCRIPT%
  pause
  exit /b 19
)
"%PY%" -I -B -S "%SCRIPT%" --root "%ROOT%" --package "%PACKAGE_DIR%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [COMPLETE] C4 dual-profile baseline sealed and C4 closed.
) else (
  echo [STOPPED] C4F failed closed with exit code %RC%.
)
pause
exit /b %RC%
