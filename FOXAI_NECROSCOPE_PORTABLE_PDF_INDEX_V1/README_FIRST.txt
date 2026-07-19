FOXAI NECROSCOPE PORTABLE PDF INDEX V1

WHY THIS BUILD EXISTS

The read-only source preflight confirmed that all six owned local books are
present, totaling 1,011 PDF pages. It also confirmed that FOXAI did not yet
have a local PDF text extractor.

This package solves only that missing infrastructure step.

WHAT IT DOES

- Carries an isolated pure-Python copy of pypdf 5.9.0
- Does not install pypdf into FOXAI's main Python environment
- Opens the six source PDFs read-only
- Extracts text page by page
- Builds a private SQLite source database
- Uses SQLite FTS5 when the portable runtime supports it
- Falls back to ordinary literal search when FTS5 is unavailable
- Produces page leads for:
  - Agent-Managed Deck and MasterDeck rules
  - Core resolution and Value Chart rules
  - Character creation
  - E-Branch, deadspeak, Wamphyri, psionics, and setting lore
- Flags image-heavy or low-text pages for later visual review
- Preserves page numbers for grounded Agent Fox citations

WHAT IT DOES NOT DO

- It does not modify, rename, move, copy, or upload any source PDF.
- It does not use the internet.
- It does not OCR image-only pages.
- It does not change FOXAI's runtime packages.
- It does not expose the private books to GitHub or the network.
- It does not yet run the campaign.

OUTPUT

Z:\FOXAI\Projects\NecroscopeCampaign\SourceIndexV1

The folder will contain:

- necroscope_sources.sqlite3
- necroscope_index_report.md
- necroscope_page_leads.md
- LATEST.txt

INSTALL AND RUN

1. Extract this entire folder directly inside:
   Z:\FOXAI

2. Open:
   Z:\FOXAI\FOXAI_NECROSCOPE_PORTABLE_PDF_INDEX_V1

3. Run:
   RUN_NECROSCOPE_PDF_INDEX.bat

4. Press Y.

5. When complete, test it with:
   SEARCH_NECROSCOPE_INDEX.bat

Suggested searches:

- MasterDeck
- subplot card
- result points
- difficulty number
- character creation
- E-Branch
- deadspeak

6. Upload these two generated reports:

- necroscope_index_report.md
- necroscope_page_leads.md

NEXT BUILD

After the reports confirm usable extraction, the next build is:

NECROSCOPE CAMPAIGN ROOM V1

That build will connect Agent Fox to the private page index, provide book/page
citations, create a campaign journal and character state, and implement the
Agent-Managed Deck using the exact card rules located in Eric's owned books.

THIRD-PARTY COMPONENT

pypdf 5.9.0 is bundled in an isolated vendor folder.
Its license is included under THIRD_PARTY_LICENSES.
