KAYOCK'S STUDY V2B.3 R2
LOCAL READ-ALOUD WITH COMPATIBLE READER REGRESSION
Exact Engineering Workshop Plan

Mission:
ENG-20260720-181903-DE1EBD

WHY THIS IS R2
--------------
The first V2B.3 attempt was safely rolled back because it ran the historical
V2B.2 verifier after upgrading the application. That historical verifier is
intentionally version-locked to APP_VERSION 2B.2 and intentionally requires
speechSynthesis to be absent.

R2 preserves that historical verifier unchanged but does not execute it
against V2B.3.

Instead, R2 adds a V2B.3-compatible 60-check native-reader and security
regression that re-tests the actual V2B.2 capabilities without rejecting the
new local narration feature.

RESTORED BASELINE GUARD
-----------------------
The live study_server.py must exactly match the restored V2B.2 SHA-256 before
R2 can apply:

    0eb319a36b8816df3ff824f493eb83305fe28aba76d8f067a4ce15644596bfc0

WHAT THIS ACTIVATES
-------------------
- Confirmed local Windows/browser voices only.
- Read This to Me from EPUB title pages and the built-in reader.
- Play, Pause, Resume, Stop, Previous Paragraph, Next Paragraph,
  Restart Chapter, and Read from Here.
- Click or keyboard passage selection.
- Paragraph highlighting and boundary phrase highlighting when available.
- Optional chapter advancement, off by default.
- Voice, speed, pitch, volume, and safe Test Voice controls.
- Separate narration progress and explicit Remember This Position.

VALIDATIONS
-----------
1. Source compilation
2. Study and narration-sidecar environment
3. Bibliotheca V1.2.2 search reliability — 24 checks
4. V2B.3-compatible reader and security regression — 60 checks
5. V2B.3 mocked voice, state, highlighting, and loopback — 39 checks

The historical VERIFY_KAYOCKS_STUDY_V2B_2.py remains untouched and is not
run against V2B.3.

CHANGED SOURCE FILES
--------------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2B_3_READER_COMPAT.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2B_3.py

PLAN SHA-256
------------
ac753e13f781ae21b961154a86ee6c749513868de4418aa2ffd3cd79b01c5f82

FINAL INTERACTIVE TEST
----------------------
The package verifies local/online voice filtering with mocked browser voices.
Actual sound output and Windows voice quality require Eric's final interactive
test after installation.

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V2B_3_R2_Local_Read_Aloud_Compatible_Regression\KAYOCKS_STUDY_V2B_3_R2_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-181903-DE1EBD
- Changed paths: 3
- Validations: 5
- Plan SHA-256: ac753e13f781ae21b961154a86ee6c749513868de4418aa2ffd3cd79b01c5f82
