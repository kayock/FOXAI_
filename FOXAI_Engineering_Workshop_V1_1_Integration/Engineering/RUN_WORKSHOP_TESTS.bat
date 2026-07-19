@echo off
setlocal
set "HERE=%~dp0"
for %%I in ("%HERE%..\..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
cd /d "%FOXAI_ROOT%"
"%PYTHON%" -m unittest discover -s Departments\Engineering\tests -v
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
