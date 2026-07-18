@echo off
setlocal EnableExtensions
for %%I in ("%~dp0.") do set "PACKAGE_DIR=%%~fI"
for %%I in ("%PACKAGE_DIR%\..") do set "FOXAI_ROOT=%%~fI"
set "PY=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "TEST=%PACKAGE_DIR%\System\WebUITest\usbc4e_webui_two_profile_lifecycle_test.py"

echo ================================================================
echo  FOXAI USB C4E - WebUI Two-Profile Lifecycle Test
echo ================================================================
echo.
echo Root:    %FOXAI_ROOT%
echo Package: %PACKAGE_DIR%
echo.
echo This controlled test will temporarily start FOXAI WebUI and ComfyUI.
echo No browser will open. Both services will be stopped before completion.
echo.

if not exist "%PY%" (
  echo [BLOCKED] Portable Python is missing: %PY%
  pause
  exit /b 21
)
if not exist "%TEST%" (
  echo [BLOCKED] C4E test script is missing: %TEST%
  pause
  exit /b 21
)

"%PY%" -I -B -S "%TEST%" --root "%FOXAI_ROOT%" --package "%PACKAGE_DIR%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [COMPLETE] C4E lifecycle test completed and both services were stopped.
) else (
  echo [STOPPED] C4E failed closed with exit code %RC%.
  echo Review the newest TEST_OUTPUT folder. Cleanup was attempted automatically.
)
echo.
pause
exit /b %RC%
