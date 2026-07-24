@echo off
setlocal
cd /d "%~dp0"
title Project Forge Preview 8 - Code Slicer Integration
set "PYTHON_EXE="
if exist "Z:\Hanger Bay\Development\Python\python.exe" set "PYTHON_EXE=Z:\Hanger Bay\Development\Python\python.exe"
if not defined PYTHON_EXE where py >nul 2>nul && set "PYTHON_EXE=py -3"
if not defined PYTHON_EXE where python >nul 2>nul && set "PYTHON_EXE=python"
if not defined PYTHON_EXE (
  echo Python was not found. No installer or shared runtime change was attempted.
  pause
  exit /b 1
)
echo Starting Project Forge Preview 8...
%PYTHON_EXE% project_forge_preview8.py
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo Project Forge exited with code %RC%.
  pause
)
exit /b %RC%
