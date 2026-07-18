@echo off
setlocal enabledelayedexpansion
title FOXAI - Clean Portable Startup

REM ============================================================
REM FOXAI Clean Portable Startup
REM Put this file in the root of your FOXAI folder.
REM Example:
REM   Z:\FOXAI\START_FOXAI_CLEAN.bat
REM ============================================================

set "FOXAI_ROOT=%~dp0"
set "FOXAI_ROOT=%FOXAI_ROOT:~0,-1%"
set "COMFY_DIR=%FOXAI_ROOT%\ComfyUI"
set "LOG_DIR=%FOXAI_ROOT%\Logs"
set "LOG_FILE=%LOG_DIR%\startup.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo ============================================================>> "%LOG_FILE%"
echo [%date% %time%] FOXAI startup beginning>> "%LOG_FILE%"
echo FOXAI_ROOT=%FOXAI_ROOT%>> "%LOG_FILE%"
echo COMFY_DIR=%COMFY_DIR%>> "%LOG_FILE%"

echo ==========================================
echo FOXAI - Clean Portable Startup
echo ==========================================
echo.
echo FOXAI root:
echo %FOXAI_ROOT%
echo.

REM ============================================================
REM Find Python
REM ============================================================

set "PYTHON_CMD="

if exist "%FOXAI_ROOT%\env\python\python.exe" (
    set "PYTHON_CMD=%FOXAI_ROOT%\env\python\python.exe"
) else if exist "%FOXAI_ROOT%\python\python.exe" (
    set "PYTHON_CMD=%FOXAI_ROOT%\python\python.exe"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_CMD=python"
        )
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python was not found.
    echo Install Python or place portable Python at:
    echo %FOXAI_ROOT%\env\python\python.exe
    echo.
    echo [%date% %time%] ERROR: Python not found>> "%LOG_FILE%"
    pause
    exit /b 1
)

echo [OK] Python command:
echo %PYTHON_CMD%
echo [%date% %time%] PYTHON_CMD=%PYTHON_CMD%>> "%LOG_FILE%"
echo.

REM ============================================================
REM Start ComfyUI if present and not already responding
REM ============================================================

echo Checking ComfyUI at http://127.0.0.1:8188 ...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8188' -TimeoutSec 2; exit 0 } catch { exit 1 }"

if errorlevel 1 (
    echo ComfyUI is not running.
    if exist "%COMFY_DIR%\main.py" (
        echo Starting ComfyUI from:
        echo %COMFY_DIR%
        echo [%date% %time%] Starting ComfyUI>> "%LOG_FILE%"

        start "FOXAI ComfyUI" cmd /k ""%FOXAI_ROOT%\Runtime\Desktop\python\python.exe" -I -B -S "%FOXAI_ROOT%\System\PortableRuntime\launch_comfyui_isolated.py" --root "%FOXAI_ROOT%" -- --cpu"

        echo Waiting for ComfyUI to answer...
        set /a COUNT=0

        :WAIT_COMFY
        timeout /t 2 /nobreak >nul
        set /a COUNT+=1

        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
          "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8188' -TimeoutSec 2; exit 0 } catch { exit 1 }"

        if not errorlevel 1 (
            echo [OK] ComfyUI is online.
            echo [%date% %time%] ComfyUI online>> "%LOG_FILE%"
            goto START_FOXAI
        )

        if !COUNT! GEQ 30 (
            echo [WARN] ComfyUI did not answer after about 60 seconds.
            echo FOXAI will continue anyway.
            echo [%date% %time%] WARN: ComfyUI did not answer within timeout>> "%LOG_FILE%"
            goto START_FOXAI
        )

        goto WAIT_COMFY
    ) else (
        echo [WARN] ComfyUI main.py was not found:
        echo %COMFY_DIR%\main.py
        echo FOXAI will continue without starting ComfyUI.
        echo [%date% %time%] WARN: ComfyUI missing>> "%LOG_FILE%"
    )
) else (
    echo [OK] ComfyUI already appears to be running.
    echo [%date% %time%] ComfyUI already running>> "%LOG_FILE%"
)

REM ============================================================
REM Start FOXAI
REM ============================================================

:START_FOXAI
echo.
echo ==========================================
echo Starting FOXAI...
echo ==========================================
echo.

if exist "%FOXAI_ROOT%\foxai.py" (
    echo Launching foxai.py
    echo [%date% %time%] Launching foxai.py>> "%LOG_FILE%"
    start "FOXAI" cmd /k "cd /d "%FOXAI_ROOT%" && %PYTHON_CMD% foxai.py"
    exit /b 0
)

if exist "%FOXAI_ROOT%\FoxAI_Desktop.py" (
    echo Launching FoxAI_Desktop.py
    echo [%date% %time%] Launching FoxAI_Desktop.py>> "%LOG_FILE%"
    start "FOXAI" cmd /k "cd /d "%FOXAI_ROOT%" && %PYTHON_CMD% FoxAI_Desktop.py"
    exit /b 0
)

echo [ERROR] No FOXAI entry point found.
echo Expected one of:
echo %FOXAI_ROOT%\foxai.py
echo %FOXAI_ROOT%\FoxAI_Desktop.py
echo.
echo [%date% %time%] ERROR: No FOXAI entry point found>> "%LOG_FILE%"
pause
exit /b 1
