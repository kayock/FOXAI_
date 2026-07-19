KAYOCK'S STUDY — THE BIBLIOTHECA V1.1
Read. Research. Preserve. Discover.

WHAT V1.1 ADDS

- Collection shelves based on Library folders
- A dedicated Recipes shelf when Recipes is a top-level Library folder
- Shelf, document, and text-status filters for search and Agent Fox
- Duplicate review with:
  - exact-byte duplicate detection by SHA-256
  - related-title review for files that may be alternate copies
  - a recommended keeper
  - every proposed move shown before approval
- Approved cleanup moves files only into:
  Library\Needs Review\Bibliotheca Duplicate Review
- No delete action
- Pause, resume, and stop-after-current-PDF controls
- Faster incremental refresh:
  unchanged files are skipped by size and modification time
  without rehashing or re-extracting them
- Visible elapsed time and files-per-second status
- Existing V1 SQLite database remains in place

INSTALL

1. Close Kayock's Study and its black command window.
2. Extract this complete upgrade folder directly inside Z:\FOXAI.
3. Run:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1_1_UPGRADE\
   APPLY_BIBLIOTHECA_V1_1_UPGRADE.bat

4. Press Y.
5. Restart the existing Study with:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1\
   START_KAYOCKS_STUDY.bat

The address remains:

  http://127.0.0.1:8777

PRESERVATION

The installer requires the exact reviewed V1 server SHA-256.
It backs up the V1 server and creates a consistent SQLite snapshot before
replacing one file:

  KAYOCKS_STUDY_BIBLIOTHECA_V1\study_server.py

It does not replace or delete:

- Data\bibliotheca.sqlite3
- indexed pages
- PDFs
- receipts
- logs
- the bundled pypdf runtime
- launchers

DUPLICATE REVIEW SAFETY

V1.1 never deletes a Library file. The operator must review the recommended
keeper and proposed moves, press the move button, and type:

  MOVE TO REVIEW

Moved files retain their SHA-256 and are placed under Needs Review.
A receipt records each old path, new path, and preserved hash.
