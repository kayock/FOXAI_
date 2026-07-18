@echo off
setlocal EnableExtensions
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "PACKAGE_ROOT=%%~fI"
for %%I in ("%PACKAGE_ROOT%\..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_ROOT%\System\Integration\usbc4d_apply.py"

if not exist "%PYTHON%" echo ERROR: Portable Python is missing.& pause & exit /b 2
if not exist "%SCRIPT%" echo ERROR: C4D apply script is missing.& pause & exit /b 3

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --package-root "%PACKAGE_ROOT%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo C4D completed successfully. Nothing was launched.
) else (
  echo C4D stopped safely with exit code %RC%.
)
pause
exit /b %RC%
