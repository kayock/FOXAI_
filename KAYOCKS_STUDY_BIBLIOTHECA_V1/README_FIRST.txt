KAYOCK'S STUDY — THE BIBLIOTHECA V1
Read. Research. Preserve. Discover.

PURPOSE

This is the first isolated proving build of Kayock's Study. It turns the PDFs
already stored under FOXAI\Library into a private page-level search and reading
collection called The Bibliotheca.

V1 FEATURES

- Reads every PDF recursively under FOXAI\Library
- Builds a private SQLite page index beside this application
- Searches across all indexed pages or one selected document
- Opens the original PDF at the cited page
- Labels searchable, partial, likely scanned, and searchable OCR-copy files
- Detects related original/OCR filename pairs when possible
- Lets Agent Fox answer from retrieved local pages only
- Shows exact [Document Title, p. N] citations
- Still shows retrieved cited pages when the local model is offline
- Binds only to 127.0.0.1
- Never changes or deletes an original PDF
- Writes an index receipt under:
  FOXAI\Reports\KayocksStudy\Bibliotheca

NOT IN V1

- It does not perform OCR.
- It does not download documents.
- It does not use the public internet.
- It does not yet replace the existing Iron Library screen.
- It does not alter the stable FOXAI WebUI.

INSTALL AND START

1. Extract this complete folder directly inside Z:\FOXAI.

   The resulting path should be:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1

2. Run:

   START_KAYOCKS_STUDY.bat

3. The room opens at:

   http://127.0.0.1:8777

The first start automatically begins indexing when the database is empty.
You may also press "Index or Refresh Library" inside the room.

For a console-only full refresh, run:

   INDEX_KAYOCKS_STUDY.bat

For a preflight check, run:

   VERIFY_KAYOCKS_STUDY.bat

DATA AND SAFETY

The index database is:

  KAYOCKS_STUDY_BIBLIOTHECA_V1\Data\bibliotheca.sqlite3

Deleting that database only removes the generated search index. It does not
delete or modify any PDF.

Agent Fox uses the local model at 127.0.0.1:8080. Source excerpts are treated
as untrusted reference text, so instructions found inside a PDF are ignored.
