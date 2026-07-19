# FOXAI Necroscope Portable PDF Index V1

- Built: `2026-07-18T18:13:40-06:00`
- Database: `Z:\FOXAI\Projects\NecroscopeCampaign\SourceIndexV1\necroscope_sources.sqlite3`
- Extractor: **pypdf 5.9.0 (isolated bundled copy)**
- Full-text search: **FTS5 enabled**
- Books indexed: **6**
- Pages indexed: **779**
- Extracted characters: **2,356,750**
- Low-text pages: **236**
- Pages with extraction errors: **0**

## Safety

- All source PDFs were opened read-only.
- No source PDF was modified, renamed, moved, copied, or uploaded.
- No network access was used.
- The PDF extractor is isolated inside this package; FOXAI's main Python environment was not modified.
- The database was built as a temporary file and replaced atomically only after success.

## Indexed Books

### MasterBook Corebook

- File: `Masterbook Corebook.pdf`
- Pages: `180`
- SHA-256: `4721d3a463f662da3cc9a997ada261a96264607c322fb86f05bca01701479a7a`
- Extracted characters: `0`
- Low-text pages: `180`
- Extraction-error pages: `0`

### MasterBook - World of Necroscope

- File: `MasterBook - World of Necroscope.pdf`
- Pages: `134`
- SHA-256: `f091fd10a7386f4d10879f8aa1e2bd4bb100e822d7856699437897ffda534461`
- Extracted characters: `596,586`
- Low-text pages: `12`
- Extraction-error pages: `0`

### E-Branch Guide to Psionics

- File: `MasterBook - World of Necroscope_ E-Branch Guide to Psionics.pdf`
- Pages: `130`
- SHA-256: `825fc5f3989123be4eda1020b251bf876af71c4bfeb741ee507b40c756eda224`
- Extracted characters: `492,551`
- Low-text pages: `7`
- Extraction-error pages: `0`

### Operation Nightside

- File: `[The World of Necroscope] - Operation Nightside.pdf`
- Pages: `130`
- SHA-256: `ba6922b1dc1a0007963bcd02506304f2b3677bb6880f12e9e86a7143cf62f5da`
- Extracted characters: `535,301`
- Low-text pages: `10`
- Extraction-error pages: `0`

### Wamphyri

- File: `MasterBook - World of Necroscope_ Wamphyri.pdf`
- Pages: `106`
- SHA-256: `a90dfbfa7ca9229042a8c5fe9215f50ccca651fd3a66fcc7aeff3f49fc9c7309`
- Extracted characters: `357,912`
- Low-text pages: `18`
- Extraction-error pages: `0`

### Deadspeak Dossier

- File: `MasterBook - World of Necroscope_ Deadspeak Dossier.pdf`
- Pages: `99`
- SHA-256: `155f08af350e65bafdb7d59de39457bb77d12c0d15c1963df200e755ff501eda`
- Extracted characters: `374,400`
- Low-text pages: `9`
- Extraction-error pages: `0`

## Interpretation

- Low-text pages are often covers, maps, illustrations, character sheets, or scanned-image pages. They are flagged for later visual review rather than guessed at.
- The next development step is the Necroscope Campaign Room search service and Agent-Managed Deck rules extraction.

## Quick Search

Run:

`SEARCH_NECROSCOPE_INDEX.bat`

Useful first searches:

- `MasterDeck`
- `subplot card`
- `result points`
- `difficulty number`
- `character creation`
- `E-Branch`
- `deadspeak`
