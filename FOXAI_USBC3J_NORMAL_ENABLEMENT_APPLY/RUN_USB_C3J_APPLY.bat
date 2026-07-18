@echo off
setlocal EnableExtensions
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "PACKAGE_ROOT=%%~fI"
for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_ROOT%\System\Integration\usbc3j_apply.py"

title FOXAI USB C3J - Normal Enablement Apply - NO LAUNCH
echo ============================================================
echo  FOXAI USB C3J - Normal Enablement Apply
echo  CONTROLLED WRITE - NO COMFYUI LAUNCH
echo ============================================================
echo.

if not exist "%PYTHON%" (
  echo ERROR: Portable Python is missing.
  pause
  exit /b 2
)
if not exist "%SCRIPT%" (
  echo ERROR: C3J apply script is missing.
  pause
  exit /b 3
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --package-root "%PACKAGE_ROOT%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [COMPLETE] C3J finished. ComfyUI was not launched.
) else (
  echo [STOPPED] C3J returned exit code %RC%. ComfyUI was not launched.
)
echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%
