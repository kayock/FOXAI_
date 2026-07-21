@echo off
setlocal
title FOXAI Poem Creator Guided V1.1

set "SCRIPT=%~dp0APPLY_POEM_CREATOR_GUIDED_V1_1.py"
set "PORTABLE_PY=Z:\FOXAI\Runtime\Desktop\python\python.exe"

echo.
echo FOXAI Poem Creator Guided V1.1
echo Close FOXAI WebUI before continuing.
echo.

if exist "%PORTABLE_PY%" (
  "%PORTABLE_PY%" "%SCRIPT%" %*
  set "RC=%ERRORLEVEL%"
  goto :done
)

where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%SCRIPT%" %*
  set "RC=%ERRORLEVEL%"
  goto :done
)

where python >nul 2>nul
if not errorlevel 1 (
  python "%SCRIPT%" %*
  set "RC=%ERRORLEVEL%"
  goto :done
)

echo ERROR: Python was not found.
echo Expected portable Python: %PORTABLE_PY%
set "RC=9"

:done
echo.
if "%RC%"=="0" (
  echo Finished successfully.
) else (
  echo Stopped with code %RC%. Read the message above. No unverified change should remain.
)
echo.
pause
exit /b %RC%
