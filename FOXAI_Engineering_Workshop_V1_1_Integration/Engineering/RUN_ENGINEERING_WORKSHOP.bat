@echo off
setlocal
set "HERE=%~dp0"
for %%I in ("%HERE%..\..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
cd /d "%FOXAI_ROOT%"
"%PYTHON%" -m Departments.Engineering.cli %*
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
