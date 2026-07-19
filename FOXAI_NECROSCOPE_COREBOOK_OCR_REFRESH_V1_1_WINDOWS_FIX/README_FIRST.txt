FOXAI NECROSCOPE COREBOOK OCR REFRESH V1.1 — WINDOWS FILE-HANDLE FIX

PURPOSE

Indexes:

Z:\FOXAI\Library\DnD\Masterbook Corebook_OCR_searchable.pdf

and replaces only the empty MasterBook Corebook section in the existing private
Necroscope SQLite index.

INSTALL

1. Close the Necroscope Campaign Room.
2. Extract this entire folder directly inside Z:\FOXAI.
3. Open:
   Z:\FOXAI\FOXAI_NECROSCOPE_COREBOOK_OCR_REFRESH_V1
4. Run:
   RUN_COREBOOK_OCR_REFRESH.bat
5. Press Y.

OUTPUT

Z:\FOXAI\Projects\NecroscopeCampaign\CorebookOCRRefreshV1

Upload:

masterbook_corebook_ocr_rules_packet.md

SAFETY

- Both PDFs remain unchanged.
- The current database is backed up first.
- Only masterbook_core rows are replaced.
- Other indexed books are preserved.
- The update occurs on a temporary database copy.
- SQLite integrity is checked before replacement.
- No network access or package installation occurs.

The existing Campaign Room searches the database on each turn, so it will use
the OCR corebook automatically after this refresh.


WHY V1.1 EXISTS

V1 successfully extracted the OCR corebook and generated the rules packet, but
Windows refused the final database rename because Python's sqlite3 context
manager committed the transaction without closing the file handle.

V1.1 explicitly closes the temporary SQLite connection before the atomic rename.
It also prevents cleanup from producing a second traceback if Windows briefly
holds a failed temporary build file.

RUNNING V1.1

V1.1 safely repeats the 180-page corebook refresh. It creates a fresh database
backup and a new timestamped temporary build. The failed V1 temporary `.building`
file is not used and does not affect the live database.
