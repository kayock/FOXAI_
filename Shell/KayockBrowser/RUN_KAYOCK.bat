@echo off
setlocal
cd /d "%~dp0"
title Kayock Browser 2.5.1 RC - Foundation Launcher

echo.
echo ================================================
echo   Kayock Browser 2.5.1 RC - Foundation Release
echo ================================================
echo.
echo Launcher folder:
echo %cd%
echo.

where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: Node.js was not found.
  echo.
  echo Please install Node.js LTS from:
  echo https://nodejs.org
  echo.
  echo After installing Node.js, close this window and double-click RUN_KAYOCK.bat again.
  echo.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: npm was not found, even though Node may be installed.
  echo Please reinstall Node.js LTS and make sure Add to PATH is enabled.
  echo.
  pause
  exit /b 1
)

echo Node detected:
node -v
echo npm detected:
call npm -v
echo.

if not exist package.json (
  echo ERROR: package.json was not found in this folder.
  echo Make sure you extracted the ZIP completely before running Kayock.
  echo.
  pause
  exit /b 1
)

echo Using public npm registry for this folder...
call npm config set registry https://registry.npmjs.org/ >nul 2>nul

if not exist node_modules\.bin\electron.cmd (
  echo Dependencies not ready.
  echo Installing Kayock dependencies. This can take a few minutes the first time...
  echo.
  call npm install --registry=https://registry.npmjs.org/ --no-audit --no-fund --fetch-timeout=120000 --fetch-retries=5
  if errorlevel 1 (
    echo.
    echo First install attempt failed. Trying Electron repair install...
    echo.
    call npm install electron --save-dev --registry=https://registry.npmjs.org/ --no-audit --no-fund --fetch-timeout=120000 --fetch-retries=5
    if errorlevel 1 (
      echo.
      echo ERROR: npm install failed. Copy this window text and send it with your bug report.
      echo.
      pause
      exit /b 1
    )
  )
) else (
  echo Dependencies already installed.
)

echo.
echo Starting Kayock Browser...
echo If Kayock closes immediately, copy any error text from this window.
echo.
call npx electron .

if errorlevel 1 (
  echo.
  echo ERROR: Kayock closed with an error. Copy this window text and send it with your bug report.
  echo.
  pause
  exit /b 1
)

echo.
echo Kayock Browser closed normally.
echo.
pause
