KAYOCK'S STUDY V2B.3
LOCAL READ-ALOUD AND SYNCHRONIZED HIGHLIGHTING
Exact Engineering Workshop Plan

Mission:
ENG-20260720-175733-312AD7

WHAT THIS ACTIVATES
-------------------
- Read This to Me from EPUB title pages and the built-in reader.
- Confirmed local browser/Windows voices only.
- Play, Pause, Resume, Stop, Previous Paragraph, Next Paragraph,
  Restart Chapter, and Read from Here.
- Click or keyboard selection of a passage.
- Paragraph highlighting and phrase/word highlighting when the local
  voice supplies usable boundary information.
- Optional chapter advancement, disabled by default.
- Voice, speed, pitch, and volume controls.
- A local Test Voice phrase written for FOXAI, not copied from a book.

PRIVACY AND FAIL-CLOSED BEHAVIOR
--------------------------------
Kayock's Study accepts only voices whose browser voice record explicitly
reports localService=true. Online-only and unconfirmed voices are excluded.

When no confirmed local voice exists:
- narration remains disabled;
- no book text is sent elsewhere;
- the interface explains the missing local voice.

No voice, model, or package is installed or downloaded.

SEPARATE NARRATION STATE
------------------------
Narration preferences and the latest narration paragraph are stored in:

    KAYOCKS_STUDY_BIBLIOTHECA_V1\Data\study_library_state.sqlite3

Narration progression does not silently replace normal reading position.
Use Remember This Position to deliberately update ordinary reading progress.

NOT INCLUDED
------------
- PDF narration
- Cloud text-to-speech
- Voice cloning or training
- Microphone recording
- Audiobook creation or export
- DRM bypass

CHANGED SOURCE FILES
--------------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2B_3.py

VALIDATIONS
-----------
1. Source compilation
2. Study and narration-sidecar environment
3. Bibliotheca V1.2.2 regression
4. V2B.2 native-reader and security regression
5. V2B.3 mocked-voice, highlighting, state, and loopback verification

PLAN SHA-256
------------
f55f0ada13bf7c1ea28c7930cab9b193883a9337e77ce56eaab45df25476b806

FINAL INTERACTIVE TEST
----------------------
The deterministic package verifies voice filtering and narration logic.
Actual audio quality and installed Windows voice behavior must be tested
interactively on Eric's computer after installation.

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V2B_3_Local_Read_Aloud_Synchronized_Highlighting\KAYOCKS_STUDY_V2B_3_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-175733-312AD7
- Changed paths: 2
- Validations: 5
- Plan SHA-256: f55f0ada13bf7c1ea28c7930cab9b193883a9337e77ce56eaab45df25476b806
