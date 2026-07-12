@echo off
setlocal EnableExtensions
set MISSING=0
for %%D in (
"00_START_HERE"
"Academy"
"AI"
"Interface"
"Knowledge"
"RepairBay"
"CreativeStudio"
"Projects"
"System"
"Backups"
) do (
    if exist %%D (
        echo OK: %%D
    ) else (
        echo MISSING: %%D
        set MISSING=1
    )
)
if "%MISSING%"=="0" (
    echo Structure check passed.
) else (
    echo Structure check found missing folders. Run bootstrap_kayocktheos.bat.
)
