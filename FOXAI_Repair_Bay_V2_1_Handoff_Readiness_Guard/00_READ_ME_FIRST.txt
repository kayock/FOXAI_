REPAIR BAY V2.1 — HANDOFF READINESS GUARD
Exact Engineering Workshop Plan

Mission:
ENG-20260719-234202-25814C

WHY THIS FIX EXISTS
-------------------
The calm Repair Bay Ask Engineer button could be clicked before a health scan,
which opened a generic Mission Console request with an empty Problem field.

CORRECTED BEHAVIOR
------------------
Before a scan:
- Ask Engineer is disabled
- The button says Run a Check First
- Mission Console cannot open from the guarded handoff

After a healthy scan with no Urgent or Recommended item:
- The button says No Repair Needed
- It remains disabled
- No Engineer request is prepared

With exactly one actionable finding:
- Ask Engineer becomes available
- That exact finding is attached automatically

With several actionable findings:
- The button says Choose a Finding
- The user must select a specific item
- Repair Bay never guesses which finding to send

FAIL-CLOSED PROTECTION
----------------------
- An invalid or stale finding ID is rejected
- The backend does not silently substitute another finding
- Incomplete planning text cannot open Mission Console
- A generic request ending with a blank Problem field is refused
- Repeat clicks cannot reopen the same handoff
- Failed preparation clears the handoff and keeps the Open button disabled

MANUAL ENGINEER USE
-------------------
The separate advanced card is renamed Describe a Problem Manually so it is
clearly distinct from a scan-grounded Repair Bay handoff.

SAFETY BOUNDARY
---------------
- No automatic Send
- No automatic mission staging
- No implementation authorization
- No apply command
- No repairs, writes, network use, commands, moves, renames, deletions,
  installations, restarts, or launcher changes
- Existing calm Repair Bay, Self-Repair Bay Advanced, diagnostics, and
  Launcher Index remain available

FILES MODIFIED
--------------
- core/foxai_web.py
- core/repair_bay_handoff.py
- core/VERIFY_REPAIR_BAY_V1.py

PLAN SHA-256
------------
05112fd35334cae39de211caecb17f5e42a83a340ee516b4745edd5eaf03225b

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V2_1_Handoff_Readiness_Guard\REPAIR_BAY_V2_1_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260719-234202-25814C
- Changed paths: 3
- Plan SHA-256: 05112fd35334cae39de211caecb17f5e42a83a340ee516b4745edd5eaf03225b
