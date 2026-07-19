@echo off
setlocal
cd /d "%~dp0"
set "PY=Z:\FOXAI\Runtime\Desktop\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0DIAGNOSE_WHITE_BREAD_PAGE7.py" > "%~dp0WHITE_BREAD_PAGE7_DIAGNOSTIC.json"
set "RC=%ERRORLEVEL%"
type "%~dp0WHITE_BREAD_PAGE7_DIAGNOSTIC.json"
echo.
echo Diagnostic saved to:
echo %~dp0WHITE_BREAD_PAGE7_DIAGNOSTIC.json
pause
exit /b %RC%
