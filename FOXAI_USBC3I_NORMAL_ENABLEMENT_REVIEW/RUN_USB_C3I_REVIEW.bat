@echo off
setlocal EnableExtensions
for %%I in ("%~dp0.") do set "PACKAGE_ROOT=%%~fI"
for %%I in ("%PACKAGE_ROOT%\..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_ROOT%\System\Review\usbc3i_normal_enablement_review.py"

title FOXAI USB C3I - Normal Enablement Review

echo ============================================================
echo FOXAI USB C3I - NORMAL ENABLEMENT AND RETENTION REVIEW
echo ============================================================
echo.
echo READ-ONLY / NO-LAUNCH REVIEW
echo - No ComfyUI or FOXAI launch
echo - No launcher, runtime, package, source, or custom-node changes
echo - No network access
echo - No log deletion or pruning
echo.

if not exist "%PYTHON%" (
  echo [STOPPED] Portable Python is missing.
  pause
  exit /b 2
)
if not exist "%SCRIPT%" (
  echo [STOPPED] C3I review script is missing.
  pause
  exit /b 3
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -I -B -S "%SCRIPT%" --package-root "%PACKAGE_ROOT%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [COMPLETE] C3I review completed. Nothing was launched or changed.
) else (
  echo [STOPPED] C3I exited with code %RC%. Nothing was launched or changed.
)
echo.
pause
exit /b %RC%
