KAYOCK'S STUDY V2B.1.1
TITLE PAGES, TILE ACTIONS, RATINGS, AND HOME SCAN FEEDBACK
Exact Engineering Workshop Plan

Mission:
ENG-20260720-161541-FC5BD5

WHAT THIS FIXES
---------------
- PDF and EPUB tiles and list rows open reliably.
- The home Scan for New Books control uses the same verified scanner as
  Advanced Library Tools.
- The home view shows scan start, progress, completion, and errors.
- Repeated clicks cannot start duplicate scans.
- Counts, shelves, covers, PDF tiles, and EPUB tiles refresh automatically
  after scanning completes.

UNIVERSAL TITLE PAGE
--------------------
Every PDF and EPUB opens a title page showing the information available in
the original file:

- Cover
- Title and author
- PDF pages or EPUB chapters
- Format and collection
- Publisher / creator and publication information when embedded
- Text or metadata status
- Original relative path
- Embedded description or PDF subject as the summary when available

No summary is fabricated. A clear unavailable message is shown when the
original file contains no summary metadata.

PERSONAL RATING
---------------
A private My Rating control supports 1–5 stars and Clear. Ratings are stored
only in this separate local sidecar:

    KAYOCKS_STUDY_BIBLIOTHECA_V1\Data\study_library_state.sqlite3

The proven Bibliotheca PDF database and EPUB catalog schemas are not changed.

OPENING AND FUTURE VOICE
------------------------
PDF title pages retain:

- Open PDF
- Search This Document
- Ask Agent Fox

EPUB title pages provide:

- Open or Save Original EPUB
- Honest guidance that the built-in reader arrives in V2B.2

Every title page now reserves:

- How to Open
- Read This to Me · Coming Soon

No reader or voice engine is activated in this repair. The reserved voice
control can later use chapter or page text with an approved local voice,
without sending the book online.

CHANGED SOURCE FILES
--------------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2B_1_1.py

VALIDATIONS
-----------
1. Source compilation
2. Bibliotheca V1.2 regression
3. Bibliotheca V1.2.2 regression
4. V2B.1 EPUB catalog regression
5. V2B.1.1 title-page, rating, scan, and live-loopback verification

PLAN SHA-256
------------
823d5e67ff1c6d6255f8df8b5070dd58157f585be869bb01c5618bee0dfb8ccf

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V2B_1_1_Title_Pages_Tile_Actions_Scan_Feedback\KAYOCKS_STUDY_V2B_1_1_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-161541-FC5BD5
- Changed paths: 2
- Validations: 5
- Plan SHA-256: 823d5e67ff1c6d6255f8df8b5070dd58157f585be869bb01c5618bee0dfb8ccf
