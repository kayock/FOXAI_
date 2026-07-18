@echo off
setlocal EnableExtensions
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "PY=%ROOT%\Runtime\Desktop\python\python.exe"
set "VERIFY=%ROOT%\System\Portability\verify_comfyui_known_good.py"
if not exist "%PY%" (
  echo [FAILED] Portable Python is missing: %PY%
  pause
  exit /b 19
)
if not exist "%VERIFY%" (
  echo [FAILED] Baseline verifier is missing: %VERIFY%
  pause
  exit /b 19
)
"%PY%" -I -B -S "%VERIFY%" --root "%ROOT%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo [COMPLETE] Known-good baseline verification passed.
) else (
  echo [STOPPED] Known-good baseline verification failed closed with exit code %RC%.
)
pause
exit /b %RC%
