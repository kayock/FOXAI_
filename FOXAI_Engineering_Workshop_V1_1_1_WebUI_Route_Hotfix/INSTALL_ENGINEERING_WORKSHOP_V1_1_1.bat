@echo off
setlocal
cd /d "%~dp0"
set "FOXAI_ROOT=Z:\FOXAI"
set "PYTHON_EXE=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" "%~dp0INSTALL_ENGINEERING_WORKSHOP_V1_1_1.py" --foxai-root "%FOXAI_ROOT%" %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo Hotfix command completed.
) else (
  echo Hotfix command failed with exit code %RC%.
)
pause
exit /b %RC%
