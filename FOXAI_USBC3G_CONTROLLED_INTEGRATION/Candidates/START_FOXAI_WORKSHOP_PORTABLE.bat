@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROOT=%~dp0"

echo ============================================================
echo FOXAI Portable Workshop
echo FOXAI Desktop + ComfyUI CPU
echo ============================================================
echo.

if not exist "%ROOT%START_FOXAI_DESKTOP_PORTABLE.bat" (
    echo ERROR: The verified portable Desktop launcher is missing.
    echo Nothing was launched.
    pause
    exit /b 2
)

if not exist "%ROOT%Runtime\Desktop\python\python.exe" (
    echo ERROR: The USB-owned Desktop Python runtime is missing.
    echo Nothing was launched.
    pause
    exit /b 2
)

if not exist "%ROOT%System\PortableRuntime\verify_desktop_runtime.py" (
    echo ERROR: The portable Desktop verifier is missing.
    echo Nothing was launched.
    pause
    exit /b 2
)

if not exist "%ROOT%ComfyUI\main.py" (
    echo ERROR: ComfyUI main.py is missing.
    echo Nothing was launched.
    pause
    exit /b 3
)

if not exist "%ROOT%Runtime\ComfyUI\site-packages\torch\__init__.py" (
    echo ERROR: The verified isolated ComfyUI target is missing or incomplete.
    echo FOXAI and ComfyUI were not launched.
    pause
    exit /b 4
)
if not exist "%ROOT%System\PortableRuntime\launch_comfyui_isolated.py" (
    echo ERROR: The isolated ComfyUI activator is missing.
    echo FOXAI and ComfyUI were not launched.
    pause
    exit /b 4
)

echo Verifying the USB-owned FOXAI Desktop runtime...
setlocal
set "PYTHONNOUSERSITE=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONHOME=%ROOT%Runtime\Desktop\python"
set "PYTHONPATH=%ROOT%Runtime\Desktop\site-packages;%ROOT%Runtime\Core\site-packages;%ROOT%"
"%ROOT%Runtime\Desktop\python\python.exe" -s "%ROOT%System\PortableRuntime\verify_desktop_runtime.py" --root "%ROOT%."
set "VERIFY_RC=%ERRORLEVEL%"
endlocal & set "VERIFY_RC=%VERIFY_RC%"

if not "%VERIFY_RC%"=="0" (
    echo.
    echo ERROR: Portable Desktop runtime verification failed.
    echo FOXAI and ComfyUI were not launched.
    pause
    exit /b 5
)

echo.
echo Launching ComfyUI with the existing proven CPU command...
start "ComfyUI CPU" /D "%ROOT%ComfyUI" cmd.exe /d /k ""%ROOT%Runtime\Desktop\python\python.exe" -I -B -S "%ROOT%System\PortableRuntime\launch_comfyui_isolated.py" --root "%ROOT%." -- --cpu"

echo Waiting 8 seconds before starting FOXAI Desktop...
timeout /t 8 /nobreak >nul

echo Launching FOXAI through the verified USB portable launcher...
start "FOXAI Portable Desktop" /D "%ROOT%" cmd.exe /d /k call "%ROOT%START_FOXAI_DESKTOP_PORTABLE.bat"

echo.
echo Startup requests sent.
exit /b 0
