@echo off
setlocal
title FOXAI Command OS v6.0 FOXKernel Test

cd /d "%~dp0"

echo ==========================================
echo FOXAI Command OS v6.0 FOXKernel Test
echo ==========================================
echo.

echo Running kernel status...
call FOXKERNEL_STATUS.bat

echo.
echo Running kernel command...
call FOXKERNEL_COMMAND.bat "Tell me a joke about a toaster joining Starfleet."

echo.
echo Kernel files:
echo OpsBridge\outbox\kernel_status.json
echo OpsBridge\outbox\kernel_status.txt
echo OpsBridge\outbox\kernel_latest_command.json
echo.
pause
