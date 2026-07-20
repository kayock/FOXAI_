REPAIR BAY V1.2 — LAUNCHER MAP AND PROTECTED BASELINE
Exact Engineering Workshop Plan

Mission:
ENG-20260719-223952-CF2EBB

PURPOSE
-------
Extends the installed read-only Repair Bay scanner with static launcher analysis.
It reads BAT text but never executes a launcher or command.

LAUNCHER MAP
------------
For each root BAT file, the Full Read-Only Scan records:
- Plain-English inferred purpose
- Static commands named in the file
- Child BAT launchers referenced
- Python, PowerShell, and executable references
- Parent launchers that reference it
- Likely entry-point or support status
- Engineering Workshop receipt mentions
- SHA-256 content identity for duplicate review

PROTECTED BASELINE
------------------
Protection roles cover:
- Known-good combined WebUI and ComfyUI launcher
- Known-good Desktop two-window recovery launcher
- Engineering Workshop entry points
- Kayock's Study start and verification launchers
- ComfyUI start, status, and stop lifecycle controls
- GitHub source-control workflows
- Dedicated stop controls
- Commissioning scripts
- Recovery, restore, and rollback scripts

Protected launchers are never proposed as archive-review candidates.

CONSERVATIVE REVIEW
-------------------
- Exact duplicate content is evidence, not permission to remove anything.
- Similar names are not treated as duplicates.
- "Obsolete-looking" means low-confidence manual-review candidate only.
- Unknown items remain unresolved instead of being guessed obsolete.
- The proposed archive sequence is memory-only and proposal-only.
- Any later archive action requires a new exact plan, snapshot, reversible
  destination, exact file list, and explicit approval.
- Direct deletion is never proposed.

FILES MODIFIED
--------------
- core/repair_bay_diagnostics.py
- core/VERIFY_REPAIR_BAY_V1.py

WEBUI
-----
core/foxai_web.py is not changed. Restart FOXAI WebUI after successful
application so the running process loads Repair Bay V1.2.

SAFETY
------
- No BAT execution
- No subprocess or repair commands during scans
- No network use
- No scan-time writes
- No moves, renames, deletions, archives, installations, or repairs
- No whole-drive or protected-content scan

PLAN SHA-256
------------
872b6865d8b33dd666447f87e63eade2e75c1d0a32aada5126b3f6981b11322d

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V1_2_Launcher_Map_Protected_Baseline\REPAIR_BAY_V1_2_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260719-223952-CF2EBB
- Changed paths: 2
- Plan SHA-256: 872b6865d8b33dd666447f87e63eade2e75c1d0a32aada5126b3f6981b11322d
