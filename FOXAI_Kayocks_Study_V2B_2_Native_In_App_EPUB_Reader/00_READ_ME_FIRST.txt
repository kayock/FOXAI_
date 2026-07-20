KAYOCK'S STUDY V2B.2 — NATIVE IN-APP EPUB READER
Exact Engineering Workshop Plan

Mission:
ENG-20260720-165647-AE0874

WHAT THIS BUILDS
----------------
- Read in Kayock's Study as the primary EPUB action.
- A native local reader within the existing Study interface.
- Nested table of contents and chapter navigation.
- Previous Chapter, Next Chapter, and Start from Beginning.
- Dark, Light, and Sepia reading themes.
- Book Serif, Clean Sans, and System font choices.
- Adjustable text size, line spacing, and reading width.
- Embedded images, supported fonts, publisher CSS, and internal chapter links.
- Local bookmarks.
- Per-book reading position and preference restoration.
- A Continue Reading shelf on Library Home.
- Back to Title Page navigation.

SAFE EPUB RENDERING
-------------------
The reader serves only the selected local EPUB and:

- removes scripts and inline event handlers;
- blocks forms, iframes, objects, audio, video, and executable content;
- blocks javascript:, file:, remote HTTP/HTTPS resources, and remote fonts;
- normalizes archive members and rejects path traversal;
- requires assets to be declared in the EPUB manifest;
- permits only bounded images and embedded-font asset types;
- applies archive, member-size, and compression-ratio limits;
- refuses encrypted/protected and fixed-layout EPUBs in this phase.

The original EPUB is never rewritten.

READING STATE
-------------
Progress, preferences, and bookmarks are stored only in:

    KAYOCKS_STUDY_BIBLIOTHECA_V1\Data\study_library_state.sqlite3

No reader tables are added to bibliotheca.sqlite3 or epub_catalog.sqlite3.

THORIUM AND DEFAULT-READER FALLBACK
-----------------------------------
The title page retains a secondary external-reader action.

- When an existing local Thorium installation is detected, it reads
  Open in Thorium.
- Otherwise it reads Open in Default EPUB Reader.
- Nothing is installed or downloaded.
- External handoff occurs only after an explicit user click.
- Save Original EPUB remains available as an exact preserved-file handoff.

VOICE
-----
Read This to Me remains visible as a disabled V2B.3 control. This build does
not activate browser speech synthesis, cloud TTS, or local voice models.

CHANGED SOURCE FILES
--------------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2B_2.py

VALIDATIONS
-----------
1. Source compilation
2. Study database, EPUB catalog, and reader-sidecar environment
3. Bibliotheca V1.2 exact-page and recipe regression
4. Bibliotheca V1.2.2 search API regression
5. V2B.2 reader, security, state, bookmark, Continue Reading, and loopback HTTP verification

PLAN SHA-256
------------
c4b0b058c6d71fb55d88450914f742d8dc2126db2233df3b46c541d16933f4c4

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V2B_2_Native_In_App_EPUB_Reader\KAYOCKS_STUDY_V2B_2_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-165647-AE0874
- Changed paths: 2
- Validations: 5
- Plan SHA-256: c4b0b058c6d71fb55d88450914f742d8dc2126db2233df3b46c541d16933f4c4
