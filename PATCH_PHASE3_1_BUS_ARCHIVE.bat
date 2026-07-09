@echo off
setlocal
title FOXAI Core v10 Phase 3.1 - Bus + Archive Hotfix

cd /d "%~dp0"

echo ==========================================
echo FOXAI Core v10 Phase 3.1
echo Bus + Archive Hotfix
echo ==========================================
echo.
echo This patches:
echo core\foxai_web.py
echo.
echo A backup will be created automatically.
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_PHASE3_1_BUS_ARCHIVE.py
) else (
    python PATCH_PHASE3_1_BUS_ARCHIVE.py
)

echo.
pause
