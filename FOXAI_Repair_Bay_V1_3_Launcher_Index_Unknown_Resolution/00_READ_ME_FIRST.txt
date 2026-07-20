REPAIR BAY V1.3 — LAUNCHER INDEX AND UNKNOWN RESOLUTION
Exact Engineering Workshop Plan

Mission:
ENG-20260719-225448-2AB493

PURPOSE
-------
Adds a searchable and filterable read-only Launcher Index inside Repair Bay.

INDEX FIELDS
------------
Every root BAT file can be reviewed by:
- Filename and inferred plain-English purpose
- Purpose confidence and resolution state
- Category and likely entry-point status
- Protected roles
- Parent and child launcher relationships
- Recognized commands
- Referenced Python, PowerShell, and executable files
- Engineering Workshop receipt evidence
- Exact duplicate-content membership
- Similar-name family membership
- Archive-review reasoning
- Unresolved reason

APPROVED FRONT DOORS
--------------------
The index clearly presents:
- START_FOXAI_WEB_WITH_COMFYUI.bat
- START_FOXAI_DESKTOP_TWO_WINDOW_RECOVERY.bat
- Launch FOXAI Workshop.bat
- KAYOCKS_STUDY_BIBLIOTHECA_V1/START_KAYOCKS_STUDY.bat

The first two remain the receipt-backed primary known-good launchers.
Workshop and Study are specialized protected entry points.

UNKNOWN RESOLUTION
------------------
Deeper static analysis may resolve an unknown launcher only when its text
reveals a trustworthy child BAT, Python script, PowerShell script, executable,
caller relationship, or distinctive command. Generic or uncertain scripts
remain marked unresolved with an explanation.

SAFETY
------
- BAT files are read as text only and never executed
- No commands, subprocesses, or network use during analysis
- No launcher is changed, moved, renamed, deleted, or archived
- No repair is applied
- Archive candidates remain low-confidence review information only
- Protected baseline items cannot become archive-review candidates

FILES MODIFIED
--------------
- core/foxai_web.py
- core/repair_bay_diagnostics.py
- core/VERIFY_REPAIR_BAY_V1.py

PLAN SHA-256
------------
4d359aee9fb49095e3e115443acd2f604318c47a9fffbada22a1e7647c6e7537

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V1_3_Launcher_Index_Unknown_Resolution\REPAIR_BAY_V1_3_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260719-225448-2AB493
- Changed paths: 3
- Plan SHA-256: 4d359aee9fb49095e3e115443acd2f604318c47a9fffbada22a1e7647c6e7537
