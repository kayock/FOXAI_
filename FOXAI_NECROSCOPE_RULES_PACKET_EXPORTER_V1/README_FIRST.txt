FOXAI NECROSCOPE RULES PACKET EXPORTER V1

PURPOSE

The portable PDF index successfully extracted five Necroscope/MasterBook books.
The MasterBook Corebook is present but image-only.

This exporter creates compact, page-cited preparation packets from the private
SQLite index so the exact rules can be reviewed before building the Campaign
Room and Agent-Managed Deck.

OUTPUT

Z:\FOXAI\Projects\NecroscopeCampaign\RulesPacketsV1

FILES

- agent_managed_deck_rules.md
- core_resolution_rules.md
- character_creation_rules.md
- campaign_lore_seed.md
- masterbook_corebook_ocr_status.md
- rules_packet_manifest.json
- LATEST.txt

HOW IT SELECTS PAGES

The exporter combines:

- Known high-value page leads from the successful index
- Literal searches for important rules phrases
- One neighboring context page where useful
- Strict page limits so it does not dump entire books

SAFETY

- Source PDFs remain read-only.
- The SQLite source index remains read-only.
- No network access is used.
- No packages are installed.
- Output is written only to the private campaign project folder.
- The MasterBook Corebook is not OCRed automatically.

INSTALL AND RUN

1. Extract this folder directly inside:
   Z:\FOXAI

2. Open:
   Z:\FOXAI\FOXAI_NECROSCOPE_RULES_PACKET_EXPORTER_V1

3. Run:
   RUN_NECROSCOPE_RULES_PACKET_EXPORTER.bat

4. Press Y.

5. Upload these three generated files first:

   agent_managed_deck_rules.md
   core_resolution_rules.md
   character_creation_rules.md

Those packets will provide the exact grounded rules needed for the next build.
