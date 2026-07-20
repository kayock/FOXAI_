REPAIR BAY V2.2 — RELIABLE MISSION CONSOLE TRANSFER
Exact Engineering Workshop Plan

Mission:
ENG-20260720-000505-573954

FAULT CONFIRMED
---------------
V2.1 prepared a valid handoff, but its automatic Mission Console open was
called before the preparation lock was cleared. Mission Console therefore
showed "Wait for the handoff to finish preparing" and remained empty.

CORRECTED ORDER
---------------
1. Build and validate the grounded Engineer request.
2. Store the complete nonblank request in shared WebUI session state.
3. Mark the handoff prepared only after storage succeeds.
4. Clear the preparation lock in the finally path.
5. Open Mission Console and populate its input.
6. Keep the prepared request available while navigating.

VISIBLE CONTROLS
----------------
Calm Repair Bay now displays after successful preparation:
- Open Mission Console
- Cancel Handoff

Self-Repair Bay — Advanced retains its Open in Mission Console control.

LIFECYCLE
---------
The prepared request remains available until:
- the exact request is sent;
- Cancel Handoff is selected;
- a new health scan or new handoff replaces it; or
- Mission Console is reset.

Repeated preparation of the same finding reuses the stored request and says:
"Already prepared — Open Mission Console."

FAIL-CLOSED RULES
-----------------
- Repair Bay never claims success without validated nonblank stored text.
- Mission Console input failure does not destroy the stored request.
- Blank or incomplete requests remain blocked.
- Manual review is still required before Send.
- No mission is staged and no implementation is authorized automatically.

FILES MODIFIED
--------------
- core/foxai_web.py
- core/VERIFY_REPAIR_BAY_V1.py

NOT MODIFIED
------------
- core/repair_bay_handoff.py
- Repair Bay diagnostic engine
- Engineer authorization and apply rules
- Launchers, models, libraries, Writer, Creative Studio, or Study

SAFETY
------
- No automatic Send
- No automatic mission staging
- No implementation authorization
- No repairs, writes, network use, commands, moves, renames, deletions,
  installations, restarts, or launcher changes

PLAN SHA-256
------------
a19c8ff9cc2573e6881779c8487d25addc6f58b207e37ceec685fd41f42cca54

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V2_2_Reliable_Mission_Console_Transfer\REPAIR_BAY_V2_2_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-000505-573954
- Changed paths: 2
- Plan SHA-256: a19c8ff9cc2573e6881779c8487d25addc6f58b207e37ceec685fd41f42cca54
