KAYOCK'S STUDY V2C.1
READ-ONLY MULTI-DRIVE LIBRARY DISCOVERY
Exact Engineering Workshop Plan

Mission:
ENG-20260720-184248-6DF31D

WHAT THIS BUILDS
----------------
A new Library Locations workspace where Eric explicitly approves one exact
folder at a time. FOXAI does not enumerate or crawl all drives.

For each approved location:

1. Preview supported file counts and estimated hashing workload.
2. Register the exact root.
3. Start a background read-only catalog scan.
4. Retain records when a removable drive is offline.
5. Disable, re-enable, rescan, or remove the root from the catalog only.

SUPPORTED CATALOG FORMATS
-------------------------
Read:
- EPUB, PDF, MOBI, AZW, AZW3

Listen:
- M4B, MP3, FLAC, OGG, WAV

Maps, covers, and companion images:
- JPG, JPEG, PNG, WEBP, TIF, TIFF, BMP

Executables and unsupported archives are ignored.

UNIFIED LOGICAL TITLES
----------------------
The separate external catalog groups related files under one logical title:

- Read
- Listen
- Maps & Extras
- File Locations and Editions

It preserves every exact path, format, location, hash, author, series,
narrator, duration, identifier, and metadata record it can read.

Relationships are visibly labeled:
- Confirmed
- Probable
- Needs Review

Eric may manually assign a file to another logical title or split it into a
new title. No destructive merge occurs.

DUPLICATES
----------
Exact duplicates use full SHA-256 content hashes. Probable relationships use
normalized title, author, series, identifiers, and folder context.

No copy is deleted, hidden, moved, renamed, consolidated, or overwritten.

SEPARATE STORAGE
----------------
External roots, catalog files, logical works, and manual corrections are
stored only in:

    KAYOCKS_STUDY_BIBLIOTHECA_V1\Data\external_library.sqlite3

No schema changes are made to:

- bibliotheca.sqlite3
- epub_catalog.sqlite3
- study_library_state.sqlite3

OFFLINE DRIVES
--------------
If a removable drive is absent, its catalog remains and its files are marked
Offline. They are not removed merely because the drive is unavailable.

SAFETY
------
- No automatic drive crawl
- No E:\Star Trek scan until Eric explicitly registers that exact folder
- No original-file modification
- No metadata-tag, timestamp, permission, filename, or folder changes
- No format conversion or DRM removal
- No online metadata lookup
- No download, installation, or external network use
- Movies, television, Plex, and music libraries are not modified

CHANGED SOURCE FILES
--------------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/external_library.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2C_1_READER_REGRESSION.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V2C_1.py

VALIDATIONS
-----------
1. Source compilation
2. Study, reader-state, and external-sidecar environment
3. Bibliotheca V1.2.2 reliability — 24 checks
4. EPUB reader, narration, and security regression — 60 checks
5. Multi-root discovery and live HTTP verification — 47 checks

RESTORED BASELINE GUARD
-----------------------
The live Study server must match the confirmed V2B.3 R2 SHA-256 before this
plan may apply:

    99b44d8852a1658092a94e8c79b080e0044f2c7970ab9aaa5a7378f5ae815ff4

PLAN SHA-256
------------
06efbd06ed8a76575ef94ba68b8e772ce99105e522111e62011ce43d1eeafc00

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V2C_1_Read_Only_Multi_Drive_Library_Discovery\KAYOCKS_STUDY_V2C_1_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-184248-6DF31D
- Changed paths: 4
- Validations: 5
- Plan SHA-256: 06efbd06ed8a76575ef94ba68b8e772ce99105e522111e62011ce43d1eeafc00
