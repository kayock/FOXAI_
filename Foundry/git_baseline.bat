@echo off
title KayocktheOS Git Baseline
cd /d "%~dp0.."

echo ==========================================
echo KayocktheOS Git Baseline
echo ==========================================
echo.

git --version
if %errorlevel% neq 0 (
  echo Git was not found. Install Git for Windows first.
  pause
  exit /b 1
)

if not exist .git (
  git init
)

git status
echo.
echo Suggested commands:
echo git add .
echo git commit -m "v0.9.0 git baseline and release packager"
echo git tag v0.9.0
echo.
pause
