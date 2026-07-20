KAYOCK'S STUDY V2C.1.1
UNIFIED TITLE DETAILS AND PERSISTENT AUDIOBOOK PLAYER
Exact Engineering Workshop Plan

Mission:
ENG-20260720-193036-8688F6

WHAT THIS REPAIRS
-----------------
Every unified-title card now opens a real title-details workspace by mouse,
keyboard, or an explicit View Title button.

The page separates:
- Read
- Listen
- Maps & Extras
- File Locations and Editions

The search text and scroll position are restored when returning to the title
grid.

MULTI-FILE AUDIOBOOKS
---------------------
A folder containing many MP3 files is treated as one logical audiobook rather
than unrelated music tracks.

FOXAI remembers:
- Logical audiobook
- Exact part or track
- Exact second within that part
- Playback speed
- Ordered playlist fingerprint
- Completed parts

Continue Listening returns to the correct file and second. Natural completion
advances into the next part. Start from Beginning does not silently erase a
later saved position. Remember This Position may deliberately replace it.

ONBOARD FOXAI PLAYER
--------------------
The persistent player includes:
- Play, Pause, Stop
- Seek bar
- Previous and next part
- Skip back 15 seconds
- Skip forward 30 seconds
- Volume and playback speed
- Continue Listening
- Start from Beginning
- Remember This Position
- Overall book and current-part progress
- Optional Open Externally fallback

Playback never starts automatically.

SAFE STREAMING
--------------
Audio is streamed through localhost using catalog record IDs and HTTP byte
ranges. Arbitrary paths, traversal, disabled roots, offline items, directories,
unsupported file types, and paths outside approved roots are rejected.

The complete audiobook is not copied into FOXAI or loaded into memory.

DUPLICATE-WINDOW PROTECTION
---------------------------
A short local playback lease prevents two Kayock's Study windows from
accidentally playing audiobooks at the same time.

EXISTING F AUDIOBOOKS CATALOG
-----------------------------
The existing F Audiobooks scan is preserved:
- 407 catalog records
- Existing SHA-256 hashes
- Exact paths, file sizes, and modified times
- Registered root and last-scan time
- No forced rescan

V2C.1.1 may improve logical grouping inside external_library.sqlite3 without
changing any original file.

CHANGED SOURCE FILES
--------------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/external_library.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2C_1_1_READER_REGRESSION.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2C_1_1.py

VALIDATIONS
-----------
1. Source compilation
2. Study and external-sidecar environment
3. Bibliotheca V1.2.2 reliability — 24 checks
4. EPUB reader and narration regression — 60 checks
5. Unified titles and audiobook player — 53 checks

BASELINE GUARDS
---------------
V2C.1 study_server.py:
    1c9f6c4ad727418c35c9c68e18f14c5437110b2cb8ac9f6d0e5e4128383c6f92

V2C.1 external_library.py:
    55decee8f86a8fa596672149e3bc4eafafac83ddc3db620926e043ae902abd1c

PLAN SHA-256
------------
43288b74b87a0acd8589389dfb3705ce385bfdbcae8fcd9f365b99415acd2d2f

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V2C_1_1_Unified_Title_Details_Persistent_Audiobook_Player\KAYOCKS_STUDY_V2C_1_1_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-193036-8688F6
- Changed paths: 4
- Validations: 5
- Plan SHA-256: 43288b74b87a0acd8589389dfb3705ce385bfdbcae8fcd9f365b99415acd2d2f
