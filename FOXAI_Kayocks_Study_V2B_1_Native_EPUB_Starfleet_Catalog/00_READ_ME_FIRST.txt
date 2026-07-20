KAYOCK'S STUDY V2B.1 — NATIVE EPUB DISCOVERY
AND STARFLEET ARCHIVE CATALOG
Exact Engineering Workshop Plan

Mission:
ENG-20260720-151845-F16893

WHAT THIS BUILDS
----------------
- Extends Scan for New Books to discover EPUB files under Z:\FOXAI\Library.
- Catalogs the Star Trek V2B Test Set without touching the E: master archive.
- Reads standard EPUB container and OPF metadata.
- Captures title, creator, language, identifier, publisher, date, chapter count,
  navigation presence, status, shelf, and folder-derived collection.
- Displays readable EPUBs beside PDFs in the tiled Study browser.
- Creates Fiction and Star Trek browsing choices from the existing folder tree.
- Uses embedded covers when available.
- Uses deterministic browser-generated placeholders when a cover is absent.
- Adds a clear Scan for New Books action to the visual home.

ISOLATED STORAGE
----------------
EPUB catalog state is stored separately at runtime:

    KAYOCKS_STUDY_BIBLIOTHECA_V1\Data\epub_catalog.sqlite3

Derived embedded-cover copies are stored in a disposable cache:

    KAYOCKS_STUDY_BIBLIOTHECA_V1\Data\EPUB_Covers\

The proven Bibliotheca PDF database schema is not changed.

SAFETY
------
- Original EPUB, PDF, MOBI, AZW, and AZW3 files are not rewritten.
- Malformed EPUBs and EPUBs with encryption markers are cataloged for review,
  not opened or converted.
- MOBI, AZW, and AZW3 are reported as unsupported in this phase.
- Removed ebook files are removed only from the sidecar catalog; originals are
  never deleted by the catalog cleanup.
- No E: drive or other external library root is scanned.
- No internet access, Audible access, download, install, or metadata lookup.
- V2A.1 tiled browsing, PDF search, recipes, exact-page asking, citations,
  Advanced Library Tools, and the Controlled Research Desk are preserved.

NOT YET INCLUDED
----------------
- Opening and reading EPUB chapters
- Full-text EPUB search and citations
- Read-aloud
- Reading progress
- Favorites
- Online metadata or cover matching
- Full external Star Trek archive connection

CHANGED SOURCE FILES
--------------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2B_1.py

PLAN SHA-256
------------
77f2cb7f0e10879b5f76b1b0d68ef329dec72f7e22f83d83bd89f8a299a5535d

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V2B_1_Native_EPUB_Starfleet_Catalog\KAYOCKS_STUDY_V2B_1_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-151845-F16893
- Changed paths: 2
- Validations: 4
- Plan SHA-256: 77f2cb7f0e10879b5f76b1b0d68ef329dec72f7e22f83d83bd89f8a299a5535d
