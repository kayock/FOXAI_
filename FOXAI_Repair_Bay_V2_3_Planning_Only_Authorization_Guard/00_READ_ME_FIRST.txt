REPAIR BAY V2.3 — PLANNING-ONLY AUTHORIZATION GUARD
Exact Engineering Workshop Plan

Mission:
ENG-20260720-002048-E3D099

WHY THIS FIX EXISTS
-------------------
The V2.2 transfer worked, but the generated request contained words that the
Engineering Workshop router interpreted as an implementation mission with
permission to change files.

V2.3 corrects that boundary at both ends.

HANDOFF GENERATOR
-----------------
Every Repair Bay-generated request now:
- Uses router-safe planning language
- Avoids implementation, repair, and permission-trigger words
- Predicts the Workshop route before returning the request
- Requires expected route PLAN
- Requires file-change permission NO
- Fails closed if either expectation is not met

MISSION CONSOLE
---------------
Before Send, Mission Console independently evaluates the exact stored text.

It displays:
- Expected Workshop route: PLAN
- File-change permission: NO

Send is blocked if the predicted route is IMPLEMENT or REPAIR, or if permission
would be YES.

IMPORTANT DISTINCTION
---------------------
This V2.3 correction mission is authorized to modify FOXAI because it installs
the guard. Future Repair Bay-generated planning requests are not authorized to
modify anything.

FILES MODIFIED
--------------
- core/foxai_web.py
- core/repair_bay_handoff.py
- core/VERIFY_REPAIR_BAY_V1.py

PLAN SHA-256
------------
7cb2014d62d4ba6dc2caedd1d411fa45c94a31d24a96c6f4c488a3b8be8b47bf

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Repair_Bay_V2_3_Planning_Only_Authorization_Guard\REPAIR_BAY_V2_3_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-002048-E3D099
- Changed paths: 3
- Plan SHA-256: 7cb2014d62d4ba6dc2caedd1d411fa45c94a31d24a96c6f4c488a3b8be8b47bf
