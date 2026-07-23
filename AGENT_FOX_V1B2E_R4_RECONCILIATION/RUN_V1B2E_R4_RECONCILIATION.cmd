@echo off
setlocal
cd /d Z:\FOXAI\AGENT_FOX_V1B2E_R4_RECONCILIATION
cls
echo AGENT FOX TECHNICAL CORE V1B-2E R4
echo PARTIAL-APPLY RECONCILIATION AND CLOSURE VERIFICATION
echo Mission: ENG-20260722-225500-4D0517
echo ------------------------------------------------------------
echo This verifies the two intended cleanup edits and protected routing state.
echo It does not change source files, launch a GUI/model, scan live state, or access K:.
echo.
Z:\FOXAI\Runtime\Desktop\python\python.exe -I -B -S run_v1b2e_r4_reconciliation.py
set RC=%ERRORLEVEL%
echo.
if "%RC%"=="0" (
  echo [VERIFIED] V1B-2E reconciliation completed successfully.
) else (
  echo [FAILED] One or more reconciliation checks failed. Nothing was repaired.
)
echo Copy the JSON result above and return it to Sol.
echo.
pause
exit /b %RC%
