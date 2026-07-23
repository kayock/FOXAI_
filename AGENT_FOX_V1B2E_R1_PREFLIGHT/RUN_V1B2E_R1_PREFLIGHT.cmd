@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "PYTHON=Z:\FOXAI\Runtime\Desktop\python\python.exe"
set "RUNNER=%~dp0run_v1b2e_routing_gap_preflight.py"

echo.
echo AGENT FOX TECHNICAL CORE V1B-2E R1
echo REAL GUI SHARED RESOURCE ROUTING GAP PREFLIGHT
echo Mission: ENG-20260722-223348-83B942
echo ------------------------------------------------------------
echo This performs bounded read-only static tracing of the installed
echo WebUI and Desktop message paths. It does not launch FOXAI,
echo load a model, perform a live scan, use the network, or access K:.
echo It writes only mission evidence under EngineeringWorkshop\missions.
echo.

if not exist "%PYTHON%" (
  echo [BLOCKED] Portable Desktop Python was not found:
  echo %PYTHON%
  goto :fail
)
if not exist "%RUNNER%" (
  echo [BLOCKED] Preflight runner was not found:
  echo %RUNNER%
  goto :fail
)

"%PYTHON%" -I -B -S "%RUNNER%"
if errorlevel 1 goto :fail

echo.
echo [VERIFIED] V1B-2E R1 preflight completed successfully.
echo Copy the JSON result above and return it to Sol.
echo.
pause
exit /b 0

:fail
echo.
echo [BLOCKED] Preflight did not complete. No FOXAI source files were changed.
echo Copy the complete output above and return it to Sol.
echo.
pause
exit /b 1
