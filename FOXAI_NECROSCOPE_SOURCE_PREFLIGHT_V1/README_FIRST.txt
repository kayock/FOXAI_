FOXAI NECROSCOPE SOURCE PREFLIGHT V1

This is the first small step toward the Necroscope Campaign Room.

It examines Eric's six owned local MasterBook/Necroscope PDFs and reports:
- Which books are present
- File sizes and SHA-256 fingerprints
- Page counts when available
- Whether text can be extracted
- Whether pages appear scan-heavy and may need OCR
- Page leads for MasterDeck/card rules
- Page leads for core resolution, character creation, and Necroscope lore
- Whether the collection is ready for page-grounded indexing

SAFETY
- The books are opened read-only.
- Nothing is uploaded.
- No network access is used.
- No software is installed.
- Reports are created only under:
  Z:\FOXAI\Projects\NecroscopeCampaign\Preflight

RUN
1. Extract this folder directly into Z:\FOXAI
2. Open Z:\FOXAI\FOXAI_NECROSCOPE_SOURCE_PREFLIGHT_V1
3. Run RUN_NECROSCOPE_SOURCE_PREFLIGHT.bat
4. Press Y
5. Upload the newest Markdown report from the Preflight folder

The script automatically tries local PyMuPDF, pypdf/PyPDF2, or Poppler
pdftotext. If none exists, it still inventories and hashes the books and says
honestly that a text extractor is needed.

Agent-Managed Deck remains the intended default campaign mode.
