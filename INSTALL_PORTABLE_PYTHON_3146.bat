@echo off
setlocal
title Install Portable Python for FOXAI

set "ROOT=Z:\FOXAI"
set "PYVER=3.14.6"
set "PYURL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip"
set "DOWNLOADS=%ROOT%\_downloads"
set "PYDIR=%ROOT%\env\python"
set "ZIP=%DOWNLOADS%\python-%PYVER%-embed-amd64.zip"

echo.
echo ============================================================
echo   FOXAI Portable Python Installer
echo ============================================================
echo Root: %ROOT%
echo Target: %PYDIR%
echo Version: Python %PYVER%
echo.

if not exist "%ROOT%" (
    echo ERROR: %ROOT% does not exist.
    echo Make sure your FOXAI drive is mounted as Z:
    pause
    exit /b 1
)

if not exist "%ROOT%\core\foxai_web.py" (
    echo WARNING: %ROOT%\core\foxai_web.py was not found.
    echo Continuing anyway, but check your FOXAI path.
    echo.
)

if not exist "%DOWNLOADS%" mkdir "%DOWNLOADS%"
if not exist "%ROOT%\env" mkdir "%ROOT%\env"

if exist "%PYDIR%\python.exe" (
    echo Existing portable Python found:
    echo %PYDIR%\python.exe
    echo.
    echo Backing it up before replacing...
    for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set "D=%%d%%b%%c"
    for /f "tokens=1-2 delims=:." %%a in ("%time%") do set "T=%%a%%b"
    set "BACKUP=%ROOT%\env\python_backup_%D%_%T%"
    move "%PYDIR%" "%BACKUP%"
    echo Backup created:
    echo %BACKUP%
    echo.
)

echo Downloading official Python embeddable package...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%PYURL%' -OutFile '%ZIP%'"

if not exist "%ZIP%" (
    echo ERROR: Download failed.
    pause
    exit /b 1
)

echo.
echo Extracting Python to:
echo %PYDIR%
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%ZIP%' -DestinationPath '%PYDIR%' -Force"

if not exist "%PYDIR%\python.exe" (
    echo ERROR: python.exe was not created.
    pause
    exit /b 1
)

echo.
echo Enabling import site in python ._pth file...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$pth=Get-ChildItem '%PYDIR%\python*._pth' | Select-Object -First 1; if($pth){(Get-Content $pth.FullName) -replace '#import site','import site' | Set-Content $pth.FullName -Encoding ASCII; Write-Host 'Updated:' $pth.FullName}else{Write-Host 'No ._pth file found'}"

echo.
echo Creating portable FOXAI launcher...
(
echo @echo off
echo cd /d "%%~dp0"
echo "%%~dp0env\python\python.exe" "%%~dp0core\foxai_web.py"
echo pause
) > "%ROOT%\START_FOXAI_WEB_PORTABLE.bat"

echo Creating portable Python verifier...
(
echo @echo off
echo cd /d "%%~dp0"
echo "%%~dp0env\python\python.exe" -c "import sys,json,os,pathlib,http.server,urllib.parse,datetime,subprocess,py_compile,shutil,importlib.util; print('PORTABLE PYTHON OK'); print(sys.version); print(sys.executable)"
echo pause
) > "%ROOT%\VERIFY_PORTABLE_PYTHON.bat"

echo.
echo Testing portable Python...
"%PYDIR%\python.exe" -c "import sys,json,os,pathlib,http.server,urllib.parse,datetime,subprocess,py_compile,shutil,importlib.util; print('PORTABLE PYTHON OK'); print(sys.version); print(sys.executable)"

if errorlevel 1 (
    echo.
    echo ERROR: Portable Python test failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS
echo ============================================================
echo Portable Python installed at:
echo %PYDIR%
echo.
echo New launcher created:
echo %ROOT%\START_FOXAI_WEB_PORTABLE.bat
echo.
echo Verifier created:
echo %ROOT%\VERIFY_PORTABLE_PYTHON.bat
echo.
echo Next:
echo 1. Run START_FOXAI_WEB_PORTABLE.bat
echo 2. Open Kayock Command OS
echo 3. Run Env Verify again
echo.
pause
exit /b 0