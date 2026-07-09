@echo off
setlocal
title FOXAI Capability Manager v2 Patch

cd /d "%~dp0"

echo ==========================================
echo FOXAI Capability Manager v2 Patch
echo ==========================================
echo.
echo This patches:
echo core_v10\capability_adapter.py
echo core_v10\mission_bus.py
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_CAPABILITY_MANAGER_V2.py
) else (
    python PATCH_CAPABILITY_MANAGER_V2.py
)

echo.
pause
