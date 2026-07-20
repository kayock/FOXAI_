KAYOCK'S STUDY V2A.1 — TILED LIBRARY BROWSER SHELL
Exact Engineering Workshop Plan

Mission:
ENG-20260720-071315-D68205

WHAT THIS BUILDS
----------------
- Makes the tiled visual browser the normal Kayock's Study home.
- Adds portrait cover-shaped document tiles.
- Adds horizontally browsable shelf rows.
- Adds Tile View and List View.
- Adds Recently Added using existing indexed_at metadata.
- Creates deterministic placeholder cover artwork in browser CSS/JavaScript.
  No cover image files are generated.
- Adds a document details window with:
  - Open PDF
  - Search This Document
  - Ask Agent Fox
- Keeps the full technical Bibliotheca workspace under Advanced Library Tools.

WHAT REMAINS UNCHANGED
----------------------
- Existing /api/status, /api/shelves, /api/documents, /api/search, /pdf,
  and /api/ask behavior
- Bibliotheca V1.2 exact-page asking and recipe intelligence
- Bibliotheca V1.2.2 search reliability
- Controlled Research Desk
- Indexing and duplicate review
- Main FOXAI port-8777 lifecycle
- Database schema and indexed content
- PDFs, EPUBs, saved research, Writer, Poetry Studio, and Repair Bay

NOT INCLUDED IN V2A.1
---------------------
- Native EPUB reading or indexing
- Favorites or reading-position storage
- Audiobooks
- Online metadata matching
- Thumbnail extraction
- External library scanning
- Star Trek test-set or E: archive changes

CHANGED FILES
-------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2A_1.py

PLAN SHA-256
------------
79dffd59bc58d3bf0310e9c5f57e458add4d60308adf5f1095fc90cdb72df1f0

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V2A_1_Tiled_Library_Browser_Shell\KAYOCKS_STUDY_V2A_1_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-071315-D68205
- Changed paths: 2
- Validations: 4
- Plan SHA-256: 79dffd59bc58d3bf0310e9c5f57e458add4d60308adf5f1095fc90cdb72df1f0
