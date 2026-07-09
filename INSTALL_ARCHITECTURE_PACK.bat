@echo off
setlocal
title FOXAI Project Orion Architecture Pack

cd /d "%~dp0"

echo ==========================================
echo FOXAI Project Orion Architecture Pack
echo ==========================================
echo.

if not exist "Z:\FOXAI" (
    echo ERROR: Z:\FOXAI not found.
    pause
    exit /b 1
)

if not exist "Z:\FOXAI\Architecture" (
    mkdir "Z:\FOXAI\Architecture"
)

xcopy /E /Y /I "Architecture" "Z:\FOXAI\Architecture"

echo.
echo Installed architecture documents to:
echo Z:\FOXAI\Architecture
echo.
pause
