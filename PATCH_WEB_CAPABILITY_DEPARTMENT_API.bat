@echo off
setlocal
title FOXAI Web Capability + Department API Patch

cd /d "%~dp0"

echo ==========================================
echo FOXAI Web Capability + Department API Patch
echo ==========================================
echo.
echo This patches:
echo core\foxai_web.py
echo.

where py >nul 2>nul
if not errorlevel 1 (
    py -3 PATCH_WEB_CAPABILITY_DEPARTMENT_API.py
) else (
    python PATCH_WEB_CAPABILITY_DEPARTMENT_API.py
)

echo.
pause
