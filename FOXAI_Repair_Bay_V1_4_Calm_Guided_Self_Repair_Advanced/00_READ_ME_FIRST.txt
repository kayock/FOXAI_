REPAIR BAY V1.4 — CALM GUIDED VIEW
WITH SELF-REPAIR BAY — ADVANCED
Exact Engineering Workshop Plan

Mission:
ENG-20260719-230742-46DF78

PURPOSE
-------
Makes Repair Bay understandable for nontechnical users without removing any
existing diagnostic or engineering capability.

DEFAULT: REPAIR BAY
-------------------
The default screen now shows:
- One clear status: Ready, Healthy, Needs Attention, or Urgent
- A short plain-English explanation
- Only genuine Urgent or Recommended items
- One safe best next step
- Check My Computer
- Run a Deeper Check
- Ask Engineer

Technical counts, evidence, paths, launcher relationships, and proposal-only
steps remain behind Show scan details.

ADVANCED: SELF-REPAIR BAY — ADVANCED
------------------------------------
The advanced panel preserves:
- Full evidence and diagnostic findings
- Launcher Index
- FOXAI readiness checks
- Scan Bridge and findings
- Proposed repair actions
- Repair history and technical tools
- Snapshot, exact-plan, validation, and receipt expectations

"Self-Repair" does not mean silent or automatic repair. Any future real change
must still require a separate exact plan, snapshot, explicit approval,
validation, and receipt.

PLAIN-ENGLISH SUMMARY
---------------------
Common findings receive layman-friendly explanations, including:
- Too many old launcher files
- High memory use from a local model or heavy application
- Low disk space
- Confirmed Windows restart needs
- Missing FOXAI components
- Damaged source or configuration
- Bibliotheca database trouble
- Oversized logs

FILES MODIFIED
--------------
- core/foxai_web.py
- core/VERIFY_REPAIR_BAY_V1.py

NOT MODIFIED
------------
- Diagnostic engine
- BAT launchers
- Models, libraries, Study database, Writer, or Creative Studio
- Repair powers or authorization rules

SAFETY
------
- No repair power added
- No automatic or silent self-modification
- No BAT execution
- No network, commands, or scan-time writes
- No moving, renaming, deleting, archiving, or installing
- Existing Repair Bay V1.3 reports and Launcher Index remain available

PLAN SHA-256
------------
f6738798e4185a74f32cdee9416a819a208157810230ad47d915769bdaeede8e

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V1_4_Calm_Guided_Self_Repair_Advanced\REPAIR_BAY_V1_4_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260719-230742-46DF78
- Changed paths: 2
- Plan SHA-256: f6738798e4185a74f32cdee9416a819a208157810230ad47d915769bdaeede8e
