REPAIR BAY V1 — READ-ONLY SCAN AND DIAGNOSE
Exact Engineering Workshop Plan

Mission:
ENG-20260719-214716-6576E8

PURPOSE
-------
Adds a practical civilian workstation diagnostic to the existing Repair Bay.

QUICK HEALTH SCAN
- Read-only safety contract
- Windows and Python host profile
- FOXAI drive free space
- Current Windows memory pressure
- Windows uptime and pending-restart signals
- Essential FOXAI components
- Known-good launcher presence and non-zero size
- Key Python source syntax using AST only
- Local GGUF model presence
- Bibliotheca SQLite quick-check in read-only mode
- Engineering Workshop snapshot and receipt evidence

FULL READ-ONLY SCAN
Includes Quick Health Scan plus:
- All live core and Study Python source syntax
- Config JSON parsing
- Zero-byte live source, config, and Study launcher detection
- Log folder growth
- FOXAI root launcher count and clutter guidance

RESULTS
-------
Every finding is ranked:
- Urgent
- Recommended
- Informational
- Healthy

Repair steps are proposal-only. Repair Bay V1 cannot apply them.

SAFETY CONTRACT
---------------
- No internet or network access
- No local commands or subprocesses during scans
- No files written during scans
- No registry writes
- No service or settings changes
- No package installation
- No repair actions
- No whole-drive scan
- No protected credential, secret, key, or vault scan
- Bibliotheca is opened read-only
- Python validation uses AST parsing and writes no bytecode

FILES CHANGED
-------------
- core/foxai_web.py

FILES ADDED
-----------
- core/repair_bay_diagnostics.py
- core/VERIFY_REPAIR_BAY_V1.py

PLAN SHA-256
------------
7ad73d05a0002477eeff6b316f9e044128a1125f85dfd57a34051c1e203e1de6

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V1_Read_Only_Scan_Diagnose\REPAIR_BAY_V1_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260719-214716-6576E8
- Changed paths: 3
- Plan SHA-256: 7ad73d05a0002477eeff6b316f9e044128a1125f85dfd57a34051c1e203e1de6

Nothing should be applied until Workshop prints the exact apply command.
