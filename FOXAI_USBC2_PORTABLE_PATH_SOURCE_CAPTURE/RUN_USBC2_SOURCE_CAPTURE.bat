@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo ============================================================
echo FOXAI USB Commissioning C2
echo Portable Path Source Capture - READ ONLY
echo ============================================================
echo.
set "FOXAI_ROOT="
for %%R in ("%~dp0.." "%~dp0\..\.." "%~dp0") do (
  if exist "%%~fR\COMMISSION_FOXAI_USB.bat" if exist "%%~fR\System\Commissioning\commission_usb.py" (
    set "FOXAI_ROOT=%%~fR"
    goto :ROOT_FOUND
  )
)
:ROOT_FOUND
if not defined FOXAI_ROOT (
  echo ERROR: FOXAI root was not found.
  echo Extract this complete folder inside the correct FOXAI repository.
  pause
  exit /b 1
)
set "PY=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
if not exist "%PY%" (
  echo ERROR: Full portable Desktop Python was not found:
  echo %PY%
  pause
  exit /b 1
)
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONHOME="
set "PYTHONPATH=%FOXAI_ROOT%\Runtime\Desktop\site-packages;%FOXAI_ROOT%\Runtime\Core\site-packages"
echo FOXAI root: %FOXAI_ROOT%
echo Controller: %PY%
echo PYTHONPATH: %PYTHONPATH%
echo.
"%PY%" -s "%~dp0capture_commissioning_sources.py" --root "%FOXAI_ROOT%" --bundle "%~dp0."
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo Source capture completed and verified.) else (echo Source capture stopped with exit code %RC%.)
echo Upload the newest CAPTURE_OUTPUT\...\UPLOAD_THIS folder.
pause
exit /b %RC%
