# FOXAI Necroscope Corebook OCR Refresh V1

- Completed: `2026-07-18T19:37:53-06:00`
- OCR file: `Masterbook Corebook_OCR_searchable.pdf`
- OCR SHA-256: `3a2a2b5f12ea2b2b8516e3675ac65d09602f6efefc46b847f8c177f6b295e7a6`
- Pages indexed: **180**
- Extracted characters: **1,049,283**
- Low-text pages: **4**
- Extraction-error pages: **0**
- FTS5 updated: **True**
- Previous database backup: `Z:\FOXAI\Projects\NecroscopeCampaign\SourceIndexV1\Backups\necroscope_sources_before_corebook_ocr_20260718T193753.sqlite3`

## Safety

- The OCR PDF was opened read-only.
- The original non-OCR corebook was not touched.
- Only the `masterbook_core` rows were replaced.
- The other five indexed books were not changed.
- The database was updated on a temporary copy and replaced only after integrity verification.
- No network access was used.

## Results

- MasterDeck/card search terms found: **9**
- Core-rule search terms found: **8**

The existing Campaign Room reads the SQLite index on every turn, so it can use the OCR corebook automatically.
