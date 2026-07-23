@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_STATE_CHECK.ps1"
if errorlevel 1 (
  echo.
  echo [ERROR] State check failed. No files were changed.
)
echo.
pause
endlocal
