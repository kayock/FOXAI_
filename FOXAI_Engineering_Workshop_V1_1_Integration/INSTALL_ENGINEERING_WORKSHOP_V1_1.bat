@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE=python"
if exist "Z:\FOXAI\Runtime\Desktop\python\python.exe" set "PYTHON_EXE=Z:\FOXAI\Runtime\Desktop\python\python.exe"

if /I "%~1"=="--approve" goto APPLY

"%PYTHON_EXE%" INSTALL_ENGINEERING_WORKSHOP_V1_1.py --foxai-root "Z:\FOXAI"
echo.
echo Preview complete. Nothing was changed.
echo After reviewing it, run this file again as:
echo INSTALL_ENGINEERING_WORKSHOP_V1_1.bat --approve
pause
exit /b %errorlevel%

:APPLY
"%PYTHON_EXE%" INSTALL_ENGINEERING_WORKSHOP_V1_1.py --foxai-root "Z:\FOXAI" --approve
set "RC=%errorlevel%"
echo.
if "%RC%"=="0" (
  echo Engineering Workshop V1.1 integration installed and verified.
) else (
  echo Installation did not verify. The backup was restored automatically.
)
pause
exit /b %RC%
