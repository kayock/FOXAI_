@echo off
setlocal
title FOXAI - Stop Chat Engine on Port 8080

echo ==========================================
echo FOXAI Stop Chat Engine on Port 8080
echo ==========================================
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do (
    echo Found process on port 8080: %%a
    taskkill /F /PID %%a
)

echo.
echo If no process was listed above, nothing was listening on port 8080.
pause
