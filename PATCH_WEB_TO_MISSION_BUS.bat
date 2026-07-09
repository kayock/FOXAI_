@echo off
setlocal
title FOXAI Core v10 Phase 3 - Wire Web Console to Mission Bus

cd /d "%~dp0"

echo ==========================================
echo FOXAI Core v10 Phase 3
echo Web Console to Mission Bus
echo ==========================================
echo.
echo This patches:
echo core\foxai_web.py
echo.
echo It requires:
echo core_v10\mission_bus.py
echo.
echo A backup will be created automatically.
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_WEB_TO_MISSION_BUS.py
) else (
    python PATCH_WEB_TO_MISSION_BUS.py
)

echo.
pause
