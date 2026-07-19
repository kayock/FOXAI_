FOXAI MASTERBOOK CARD DECK CHAPTER EXPORTER V1

PURPOSE

The broad OCR rules packet found the Card Deck chapter but its 80-page export
limit filled with earlier rule pages. This focused exporter retrieves only:

PDF pages 118 through 135

That range covers Chapter Five: The Card Deck, including:

- Anatomy of a Card
- Anatomy of the Card Deck
- Number of Cards
- The Hand vs. The Pool
- Enhancement Cards
- Subplot Cards
- Picture Cards
- Cards in Combat and Interaction
- Initiative
- Approved Action
- Critical Skill Resolution
- Getting Cards
- Examples of Card Play

DATABASE VERIFICATION

The exporter first checks the live Necroscope SQLite database.

- If the OCR corebook is present and useful there, the packet says:
  Database corebook verified: True

- If the database refresh did not complete, it reads the OCR PDF directly so
  development does not stop.

SAFETY

- Read-only source access
- No database modification
- No PDF modification
- No package installation
- No network access

INSTALL AND RUN

1. Extract this folder directly inside Z:\FOXAI.
2. Open:
   Z:\FOXAI\FOXAI_MASTERBOOK_CARD_DECK_CHAPTER_EXPORTER_V1
3. Run:
   RUN_CARD_DECK_CHAPTER_EXPORTER.bat

OUTPUT

Z:\FOXAI\Projects\NecroscopeCampaign\CardDeckChapterV1

Upload:

masterbook_card_deck_chapter_pages_118_135.md

That file will provide the exact rules needed to replace the temporary FOXAI
Story Deck with authentic Agent-Managed MasterDeck behavior.
