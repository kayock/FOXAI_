@echo off
cd /d "%~dp0"

git config --global --add safe.directory "%CD%"

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin https://github.com/kayock/FOXAI_.git
) else (
    git remote set-url origin https://github.com/kayock/FOXAI_.git
)

git branch -M main

echo.
echo GitHub remote is now set to:
git remote -v

pause