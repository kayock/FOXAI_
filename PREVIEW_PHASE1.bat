@echo off
setlocal
set "BUNDLE=%~dp0"
set "PY=%BUNDLE%..\env\python\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%BUNDLE%tools\phase1_bundle.py" preview %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo Preview passed. No live files were changed.) else (echo Preview blocked or failed. Review preview_output\PREVIEW_RECEIPT.json.)
pause
exit /b %RC%
