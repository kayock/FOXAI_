@echo off
setlocal EnableExtensions
for %%I in ("%~dp0.") do set "PACKAGE_DIR=%%~fI"
for %%I in ("%PACKAGE_DIR%\..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%PACKAGE_DIR%\System\Review\usbc4c_webui_profile_review.py"

echo ================================================================
echo  FOXAI USB C4C - WebUI Approved Custom-Node Profile Review
echo  READ-ONLY / NO LAUNCH / NO WEBUI CHANGE
echo ================================================================
echo.
if not exist "%PYTHON%" echo ERROR: Portable Python is missing.& pause & exit /b 2
if not exist "%SCRIPT%" echo ERROR: C4C review script is missing.& pause & exit /b 3
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --package "%PACKAGE_DIR%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [COMPLETE] C4C WebUI profile review passed.
) else (
  echo [STOPPED] C4C failed closed with exit code %RC%.
)
echo.
pause
exit /b %RC%
