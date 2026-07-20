REPAIR BAY V1.1 — DIAGNOSTIC ACCURACY AND LAUNCHER INVENTORY
Exact Engineering Workshop Plan

Mission:
ENG-20260719-222305-689970

PURPOSE
-------
Refines the already-installed Repair Bay V1 scanner without adding repair power.

CORRECTIONS
-----------
- Healthy findings now always say: No action required.
- Empty Python __init__.py package markers are recognized as valid.
- Windows Update and Component Based Servicing restart signals remain Recommended.
- A lone PendingFileRenameOperations marker is Informational, not proof of a Windows Update restart.
- The marker is never cleared automatically.

LAUNCHER INVENTORY
------------------
The Full Read-Only Scan now classifies root BAT files as:
- Known-good active
- Likely active
- Historical/build/patch
- Verification/status
- Unknown

It also reports:
- Exact duplicate-content groups using read-only SHA-256 comparison
- Conservative similar-name families
- Category counts and representative filenames

It does not move, rename, delete, rewrite, execute, or archive any launcher.

FILES MODIFIED
--------------
- core/repair_bay_diagnostics.py
- core/VERIFY_REPAIR_BAY_V1.py

WEBUI
-----
core/foxai_web.py is not changed. Restart FOXAI WebUI after successful application
so the running Python process loads the refined diagnostic module.

SAFETY
------
- No network use
- No subprocess or repair commands during scans
- No scan-time writes
- No registry writes
- No service or setting changes
- No packages, deletions, renames, or repairs

PLAN SHA-256
------------
98870064be6899b1de0a144a0122609bb0e6ae3d6cd02be5e8b7dc0f8a847501

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V1_1_Diagnostic_Accuracy_Launcher_Inventory\REPAIR_BAY_V1_1_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260719-222305-689970
- Changed paths: 2
- Plan SHA-256: 98870064be6899b1de0a144a0122609bb0e6ae3d6cd02be5e8b7dc0f8a847501
