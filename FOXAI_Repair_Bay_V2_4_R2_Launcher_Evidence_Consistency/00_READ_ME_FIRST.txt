REPAIR BAY V2.4 R2 — LAUNCHER EVIDENCE CONSISTENCY
Corrected Exact Engineering Workshop Plan

Mission:
ENG-20260720-011047-2E4EE9

WHY R1 ROLLED BACK
------------------
The V2.4 source compile passed.
The complete V2.4 verifier passed.
The third validation never tested FOXAI because its Python -c command had a
syntax error: it placed a compound for-loop after semicolons on one line.

R2 CORRECTION
-------------
- Keeps the exact same four source-file contents as V2.4 R1
- Keeps the exact same safety boundary and feature behavior
- Changes only the malformed third validation command
- Replaces the invalid one-line for-loop with explicit safety checks for the
  scan report and Launcher Index report
- Executes the corrected command successfully during package simulation

FILES MODIFIED
--------------
- core/foxai_web.py
- core/repair_bay_diagnostics.py
- core/repair_bay_handoff.py
- core/VERIFY_REPAIR_BAY_V1.py

SAFETY
------
- No BAT execution
- No launcher movement, rename, archive, deletion, or content change
- No automatic Send, staging, or application
- No network or repair commands
- Planning-only Engineer route remains enforced

PLAN SHA-256
------------
020b0143669728b4c194986482d93e55fce9dd4f91aa7a674f3579310a62f82e

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V2_4_R2_Launcher_Evidence_Consistency\REPAIR_BAY_V2_4_R2_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-011047-2E4EE9
- Changed paths: 4
- Plan SHA-256: 020b0143669728b4c194986482d93e55fce9dd4f91aa7a674f3579310a62f82e
