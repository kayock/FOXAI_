@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title FOXAI Extension Manager Safe State Controls Phase 2 Preview
set "PY="
set "ARGS="
if exist "..\env\python\python.exe" (set "PY=..\env\python\python.exe") else if exist "..\python\python.exe" (set "PY=..\python\python.exe") else (where py >nul 2>nul && (set "PY=py"&set "ARGS=-3") || (where python >nul 2>nul && set "PY=python"))
echo.
echo FOXAI EXTENSION MANAGER SAFE STATE CONTROLS
echo PHASE 2 EXACT PREVIEW
echo.
echo This package cannot install the candidate or change live state.
echo.
if not defined PY (echo ERROR: Python was not found.&echo Extract EMS2P directly inside Z:\FOXAI.&pause&exit /b 1)
call "%PY%" %ARGS% "%~dp0verify_preview.py"
set "RC=%ERRORLEVEL%"
echo.
echo Verifier exit code: %RC%
if not "%RC%"=="0" pause
exit /b %RC%
