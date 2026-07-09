@echo off
setlocal
title FOXAI CM v5.0a OPS Bridge Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI CM v5.0a OPS Integration Bridge Test
echo ==========================================
echo.

echo Running bridge status...
call OPS_BRIDGE_STATUS.bat

echo.
echo Running plain text mission...
call OPS_BRIDGE.bat "Tell me a joke about a toaster joining Starfleet."

echo.
echo Running JSON mission...
call OPS_BRIDGE_JSON.bat "Professor Ada, explain what MissionBus does."

echo.
echo Latest output files should now exist:
echo OpsBridge\outbox\latest_result.json
echo OpsBridge\outbox\latest_result.txt
echo.
pause
