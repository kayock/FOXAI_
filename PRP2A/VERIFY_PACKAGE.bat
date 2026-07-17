@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=%~dp0..\env\python\python.exe"
if not exist "%PYTHON%" (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 "%~dp0verify_package.py"
  ) else (
    python "%~dp0verify_package.py"
  )
) else (
  "%PYTHON%" -s "%~dp0verify_package.py"
)
pause
