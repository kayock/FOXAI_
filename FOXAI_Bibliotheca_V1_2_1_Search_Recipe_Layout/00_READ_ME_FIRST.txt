BIBLIOTHECA V1.2.1 — SEARCH AND RECIPE LAYOUT REFINEMENT
Exact Engineering Workshop Plan

Mission:
ENG-20260720-040318-034E40

WHAT THIS FIXES
---------------
The V1.2 intelligence worked, but the Search card stretched to the height of
the Ask card and left a large empty panel.

V1.2.1:
- aligns Search and Ask at the top without stretching the shorter card;
- places Page Results directly beneath the Search controls;
- moves Documents to a clean full-width row below;
- shows the actual opened document title and page;
- gives recipe results a Use This Recipe action;
- turns multiple recipe matches into clear, individually selectable choices.

USE THIS RECIPE
---------------
Choosing a recipe sets the exact document and exact page for Agent Fox. It does
not combine recipes, change recipe text, or ask the model automatically.

BACKEND PRESERVATION
--------------------
The complete Python resolver and HTTP/API sections from V1.2 are verified
byte-for-byte unchanged. The full V1.2 exact-page and recipe-intelligence
verifier is run again after installation.

FILES MODIFIED
--------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_BIBLIOTHECA_V1_2_1.py (new)

PLAN SHA-256
------------
45606a7ef4b41b06e089948925e01fedead65c6f43b445041380666add10dc9b

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Bibliotheca_V1_2_1_Search_Recipe_Layout\BIBLIOTHECA_V1_2_1_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-040318-034E40
- Changed paths: 2
- Plan SHA-256: 45606a7ef4b41b06e089948925e01fedead65c6f43b445041380666add10dc9b
