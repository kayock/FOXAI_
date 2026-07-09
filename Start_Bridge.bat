@echo off
title KayocktheOS Bridge
color 0A
cd /d "%~dp0Bridge"

if not exist node_modules (
  echo Installing Bridge dependencies...
  npm install
)

npm start
pause
