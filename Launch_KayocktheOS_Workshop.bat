@echo off
title KayocktheOS Workshop Launcher
color 0A
cd /d "%~dp0"

echo ==========================================
echo        KayocktheOS Workshop Launcher
echo ==========================================
echo.
echo Opening the Workshop...
echo.

echo [1/4] Checking Core API...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod http://127.0.0.1:8844/api/ping -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>nul
if %errorlevel% neq 0 (
    echo Core API is not responding.
    echo Starting KayocktheOS Core in a new window...
    if exist Start_KayocktheOS.bat (
        start "KayocktheOS Core" cmd /k Start_KayocktheOS.bat
        timeout /t 4 >nul
    ) else (
        echo WARNING: Start_KayocktheOS.bat was not found.
    )
) else (
    echo Core API online.
)

echo [2/4] Checking Bridge app...
if not exist Bridge\package.json (
    echo ERROR: Bridge\package.json was not found.
    echo Run Feature 002 Bridge toolkit first.
    pause
    exit /b 1
)

echo [3/4] Checking Bridge dependencies...
if not exist Bridge\node_modules (
    echo Installing Bridge dependencies...
    cd /d "%~dp0Bridge"
    npm install
    cd /d "%~dp0"
)

echo [4/4] Launching Bridge...
cd /d "%~dp0Bridge"
npm start
pause
