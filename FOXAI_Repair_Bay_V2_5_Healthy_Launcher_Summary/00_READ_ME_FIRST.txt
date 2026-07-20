REPAIR BAY V2.5 — HEALTHY LAUNCHER SUMMARY CLASSIFICATION
Exact Engineering Workshop Plan

Mission:
ENG-20260720-015120-4C285D

WHAT V2.5 CORRECTS
------------------
V2.4 made the launcher evidence accurate, but the calm Repair Bay screen still
treated launcher quantity and one exact duplicate group as a recommended repair
item even though the finalized dataset showed:
- zero unresolved-after-resolution items;
- zero evidence-backed review candidates.

V2.5 makes the calm screen, diagnostic severity, proposed repair plan, and
Engineer handoff use the same actionability rule.

HEALTHY RESULT
--------------
When unresolved items and review candidates are both zero:
- The launcher finding is informational.
- The calm screen says Your computer looks healthy.
- The calm screen says No repairs are needed.
- Ask Engineer is disabled as No Repairs Needed.
- No launcher repair-plan step is proposed.
- A direct launcher handoff request fails closed without producing an Engineer
  command.

ACTIONABLE RESULT
-----------------
Launcher review becomes actionable only when the finalized dataset contains:
- at least one unresolved-after-resolution item; or
- at least one evidence-backed low-confidence review candidate.

Launcher count, raw unknown classifications, filename wording, and exact
duplicate content alone do not qualify.

DETAILS PRESERVED
-----------------
The exact duplicate group remains visible under Show scan details and Launcher
Index. No evidence is hidden or discarded.

FILES MODIFIED
--------------
- core/foxai_web.py
- core/repair_bay_diagnostics.py
- core/repair_bay_handoff.py
- core/VERIFY_REPAIR_BAY_V1.py

SAFETY
------
- No BAT files executed or changed
- No launcher movement, rename, archive, or deletion
- No automatic Engineer Send, staging, or application
- No network or repair commands
- Existing V2.3 planning-only authorization guard remains enforced
- Existing V2.4 finalized evidence and filters remain intact

PLAN SHA-256
------------
39e949845fe0c5a87cb02772c1c543b72a43974057752792e9726052212a82ca

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V2_5_Healthy_Launcher_Summary\REPAIR_BAY_V2_5_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-015120-4C285D
- Changed paths: 4
- Plan SHA-256: 39e949845fe0c5a87cb02772c1c543b72a43974057752792e9726052212a82ca
