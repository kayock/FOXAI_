REPAIR BAY V2.4 — LAUNCHER EVIDENCE CONSISTENCY
Exact Engineering Workshop Plan

Mission:
ENG-20260720-011047-2E4EE9

FAULT CONFIRMED
---------------
The deep Repair Bay scan reported raw unknown launcher classifications as
unresolved items, while Launcher Index performed an additional static-resolution
step and correctly displayed a different unresolved count.

V2.4 creates one finalized launcher dataset used by:
- the deep Repair Bay scan;
- Launcher Index;
- Repair Bay evidence;
- the planning-only Engineer handoff.

WHAT THE INDEX NOW SHOWS
------------------------
- Every exact duplicate group with all member filenames
- Every low-confidence review candidate by exact filename
- Raw category and raw entry-point classification
- Final resolution state after static evidence is considered
- Candidate basis and filename markers
- Caller, child, receipt, command, and duplicate-group evidence
- A visible statement that filename-only cleanup is not allowed

NEW FILTERS
-----------
- Exact duplicates
- Archive-review candidates

Search now includes badges, classification and resolution states, candidate
status, duplicate membership, callers, children, receipts, commands, and other
static evidence.

CANDIDATE RULE
--------------
A word such as OLD, COPY, ALPHA, BETA, ARCHIVE, INSTALL, or PATCH is never
cleanup evidence by itself. A review candidate requires exact duplicate-content
evidence plus the existing safety exclusions. Candidate still does not mean
obsolete.

HANDOFF CORRECTION
------------------
For the launcher finding, affected paths are limited to exact low-confidence
review candidates. Protected and receipt-backed launchers are not pulled into
the affected-path list merely because their names appear in technical evidence.

FILES MODIFIED
--------------
- core/foxai_web.py
- core/repair_bay_diagnostics.py
- core/repair_bay_handoff.py
- core/VERIFY_REPAIR_BAY_V1.py

FILES NOT MODIFIED
------------------
- All BAT launcher files
- Engineering Workshop policy
- Models, libraries, Writer, Creative Studio, and Kayock's Study content

SAFETY
------
- No BAT execution
- No launcher movement, rename, archive, deletion, or content change
- No automatic Send, staging, or application
- No network or repair commands
- Planning-only Engineer route remains enforced

PLAN SHA-256
------------
404df14ee0b65688ff8c2c283d845c4e1d50c75f9c9ea91572ce05b13386184d

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V2_4_Launcher_Evidence_Consistency\REPAIR_BAY_V2_4_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-011047-2E4EE9
- Changed paths: 4
- Plan SHA-256: 404df14ee0b65688ff8c2c283d845c4e1d50c75f9c9ea91572ce05b13386184d
