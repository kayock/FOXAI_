REPAIR BAY V2 — GUARDED REPAIR HANDOFF
Exact Engineering Workshop Plan

Mission:
ENG-20260719-232100-77A8C4

PURPOSE
-------
Connects Repair Bay findings to Engineer without giving Repair Bay direct
repair power.

CALM REPAIR BAY
---------------
Urgent or Recommended items gain:
- Ask Engineer to Prepare a Fix

That action prepares a grounded planning request and opens it in Mission
Console. The operator must review it and press Send. Nothing is staged or
changed automatically.

SELF-REPAIR BAY — ADVANCED
--------------------------
Adds a Guarded Repair Handoff panel with:
- Selected finding
- Plain-English explanation
- Technical evidence
- Affected paths
- Proposed action
- Backup requirement
- Safety limits
- Prepare Exact Repair Plan
- Open in Mission Console

INITIAL SUPPORTED PLANNING CASES
--------------------------------
- Missing or empty known-good launchers
- Clearly identified missing FOXAI components
- Damaged Python through exact per-file diffs
- Invalid JSON configuration through an exact diff
- Suspicious zero-byte live files
- Reversible log archive planning
- Reversible launcher archive planning

Unsupported, broad, or uncertain findings remain advisory.

IMPORTANT BOUNDARY
------------------
The handoff prepares text for Mission Console only.

It does NOT:
- stage a mission automatically
- create an exact plan automatically
- authorize implementation
- call APPLY
- modify, move, rename, delete, install, restart, or repair anything
- run repair commands
- use the network

A later real implementation still requires:
- a reviewable exact JSON plan
- exact before hashes
- a targeted snapshot
- a separate exact APPLY hash
- explicit operator approval
- validation and automatic rollback
- a final receipt

FILES MODIFIED
--------------
- core/foxai_web.py
- core/VERIFY_REPAIR_BAY_V1.py

FILE ADDED
----------
- core/repair_bay_handoff.py

NOT MODIFIED
------------
- Repair Bay diagnostic engine
- BAT launchers
- Models, libraries, Writer, Creative Studio, or Study database
- Engineering Workshop implementation rules

PLAN SHA-256
------------
9fece5e2e6949ef0ea6923a8453f5ec1934190e4c0f098abd36538adec283f4b

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V2_Guarded_Repair_Handoff\REPAIR_BAY_V2_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260719-232100-77A8C4
- Changed paths: 3
- Plan SHA-256: 9fece5e2e6949ef0ea6923a8453f5ec1934190e4c0f098abd36538adec283f4b
