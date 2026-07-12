@echo off
cd /d "%~dp0"

git status

echo.
echo Adding all changes...
git add -A

echo.
set /p msg=Commit message: 

git commit -m "%msg%"

echo.
echo Pushing to GitHub...
git push -u origin main

echo.
pause