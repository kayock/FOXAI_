@echo off
setlocal EnableExtensions
title Search FOXAI Necroscope Source Index

for %%I in ("%~dp0..") do set "FOXAI_ROOT=%%~fI"
set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "SCRIPT=%~dp0search_necroscope_index.py"

if not exist "%PYTHON%" (
    echo ERROR: Portable Desktop Python was not found.
    pause
    exit /b 2
)

set /p "QUERY=Search the owned Necroscope books: "
if not defined QUERY (
    echo No search entered.
    pause
    exit /b 0
)

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

"%PYTHON%" -I -B -S "%SCRIPT%" --root "%FOXAI_ROOT%" --query "%QUERY%" --limit 15
echo.
pause
