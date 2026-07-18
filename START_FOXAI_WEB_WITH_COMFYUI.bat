@echo off
setlocal EnableExtensions
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "FOXAI_ROOT=%%~fI"

set "PYTHON=%FOXAI_ROOT%\Runtime\Desktop\python\python.exe"
set "QUIET_START=%FOXAI_ROOT%\System\PortableRuntime\start_comfyui_quiet.py"
set "WEB_LAUNCHER=%FOXAI_ROOT%\START_FOXAI_WEB_PORTABLE.bat"
set "WEB_URL=http://127.0.0.1:8765"

title FOXAI WebUI + ComfyUI Launcher

echo ============================================================
echo FOXAI WEBUI + COMFYUI
echo ============================================================
echo Starting ComfyUI quietly and opening FOXAI WebUI.
echo.

if not exist "%PYTHON%" (
    echo ERROR: Portable Python was not found:
    echo %PYTHON%
    pause
    exit /b 2
)
if not exist "%QUIET_START%" (
    echo ERROR: Quiet ComfyUI starter was not found:
    echo %QUIET_START%
    pause
    exit /b 3
)
if not exist "%WEB_LAUNCHER%" (
    echo ERROR: Working WebUI launcher was not found:
    echo %WEB_LAUNCHER%
    pause
    exit /b 4
)

"%PYTHON%" -I -B -S "%QUIET_START%" --root "%FOXAI_ROOT%" --source webui
if errorlevel 1 (
    echo.
    echo ERROR: ComfyUI quiet startup failed.
    echo FOXAI WebUI was not started.
    pause
    exit /b 5
)

powershell.exe -NoLogo -NoProfile -NonInteractive -Command ^
  "try { Invoke-WebRequest -UseBasicParsing -Uri '%WEB_URL%' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"

if not errorlevel 1 (
    echo FOXAI WebUI is already online. Opening browser...
    start "" "%WEB_URL%"
    timeout /t 2 /nobreak >nul
    exit /b 0
)

echo Starting FOXAI WebUI host window...
start "FOXAI WebUI" "%ComSpec%" /d /k call "%WEB_LAUNCHER%"

timeout /t 3 /nobreak >nul
exit /b 0
