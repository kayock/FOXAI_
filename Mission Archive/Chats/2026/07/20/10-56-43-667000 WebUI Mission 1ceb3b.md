# FOXAI Mission Archive

- Session ID: `20260720T105643667000_1ceb3b`
- Interface: WebUI
- Project: Default_Mission
- Professor: Agent Fox
- Model: Qwen3-30B-A3B-Q4_K_M.gguf
- Started: 2026-07-20T10:56:43

## Transcript

### ERIC — 2026-07-20T16:56:46+00:00

/engineer workshop begin Kayock’s Study V2B.2 — Native In-App EPUB Reader :: I explicitly authorize targeted Kayock’s Study server, interface, local reader-state storage, EPUB rendering, and verification changes required to open readable EPUB books directly inside Kayock’s Study. Add a primary Read in Kayock’s Study action to EPUB title pages. Open the selected book in an integrated reader within the existing FOXAI Study interface, with Back to Title Page, cover and book title context, table-of-contents navigation, previous and next chapter controls, chapter-position display, and a collapsible reading-controls panel. Render EPUB XHTML, CSS, images, SVG, and supported embedded fonts only from the selected local EPUB. Preserve headings, paragraphs, emphasis, block quotations, lists, scene breaks, internal links, and illustrations where safely possible. Block scripts, inline event handlers, forms, javascript URLs, external web resources, remote fonts, path traversal, and files outside the selected EPUB. Do not render encrypted or unsupported publications.

Add reader controls for text size, readable font choices, line spacing, content width, light, dark, and sepia themes, and continuous chapter scrolling. Store reader preferences, last chapter, last safe location within the chapter, last-opened time, and bookmarks in the existing separate local study_library_state.sqlite3 sidecar without changing bibliotheca.sqlite3 or epub_catalog.sqlite3 schemas. Resume each book at its saved position and provide Start from Beginning. Add a Continue Reading shelf to the tiled library home using the saved local reader state.

Add a narrowly scoped localhost EPUB reader API for publication metadata, spine, table of contents, sanitized chapter content, permitted local assets, reading-position updates, and bookmarks. All API access must verify the requested EPUB catalog ID, normalize archive paths, reject parent-directory traversal, enforce reasonable decompression and response-size limits, and fail with clear JSON errors without crashing Kayock’s Study.

Retain Open in Installed EPUB Reader as a secondary fallback. Detect Thorium Reader only from local Windows installation locations or executable registration already present on the computer; do not install, download, update, or contact Thorium or any online service. When Thorium is detected, label the fallback Open in Thorium. Otherwise label it Open in Default EPUB Reader. Launch an external reader only after an explicit user click and only for the selected original EPUB.

Keep the existing Read This to Me control visible but disabled with the message Voice reading arrives in V2B.3. Do not activate browser speech synthesis, cloud text-to-speech, local voice models, narration highlighting, full-book text indexing, Agent Fox EPUB citations, annotations, DRM removal, EPUB editing, conversion, fixed-layout EPUB support, audiobook support, or external library roots in this phase.

Preserve V2B.1.1 title pages, ratings, metadata summaries, tile and list actions, home Scan for New Books feedback, EPUB cover cataloging, V2A.1 tiled browsing, Bibliotheca V1.2.2 PDF search reliability, PDF opening and exact-page asking, recipes, citations, Advanced Library Tools, Controlled Research Desk, original PDFs and EPUBs, saved research, Writer, Poetry Studio, Repair Bay, models, runtimes, and the existing FOXAI port-8777 lifecycle. Do not access E:\Star Trek (ebooks), modify original books, rebuild unrelated indexes, install, download, use external network access, move, rename, or delete library content.

Add deterministic EPUB fixtures and live loopback verification covering a multi-chapter EPUB with nested table of contents, chapter styling and images, internal links, blocked scripts and remote resources, path-traversal attempts, malformed content, encrypted EPUB refusal, chapter navigation, preference persistence, reading-position resume, bookmark creation and removal, Continue Reading shelf behavior, exact original-file fallback handoff, optional Thorium detection behavior, unchanged PDF APIs, and V2B.1.1 regression checks.

### ENGINEER — 2026-07-20T16:56:47+00:00

ENGINEERING WORKSHOP — MISSION STAGED

Mission ID: ENG-20260720-165647-AE0874
Title: Kayock’s Study V2B.2 — Native In-App EPUB Reader
Route: implement
Explicit implementation authorization detected: True
Project root: Z:\FOXAI
Stage: received

No project files were changed. Next: locate relevant source or save an exact JSON plan.
