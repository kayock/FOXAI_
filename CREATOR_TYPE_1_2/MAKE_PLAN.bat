@echo off
setlocal
title FOXAI Creator Type 1.2 - Make Workshop Plan
cd /d "%~dp0"
set "PY=..\Runtime\Desktop\python\python.exe"
if exist "%PY%" goto run
where py >nul 2>nul
if not errorlevel 1 (
    set "PY=py -3"
    goto run
)
where python >nul 2>nul
if not errorlevel 1 (
    set "PY=python"
    goto run
)
echo.
echo BLOCKED - Python was not found.
echo Expected FOXAI portable Python at:
echo   ..\Runtime\Desktop\python\python.exe
echo.
pause
exit /b 1
:run
%PY% -I -B "%~dp0MAKE_PLAN.py"
exit /b %errorlevel%
