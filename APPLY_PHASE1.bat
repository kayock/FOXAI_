@echo off
setlocal
set "BUNDLE=%~dp0"
set "PY=%BUNDLE%..\env\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%BUNDLE%tools\phase1_bundle.py" apply %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo Phase 1 applied and verified.) else (echo Phase 1 was not applied, or it failed and rollback was attempted.)
pause
exit /b %RC%
