BIBLIOTHECA V1.2 — EXACT PAGE AND RECIPE INTELLIGENCE
Exact Engineering Workshop Plan

Mission:
ENG-20260720-030921-2A5D34

WHAT THIS REFINES
-----------------
This is a focused refinement of the current known-good Kayock's Study and
Bibliotheca runtime. It does not rebuild the library or its research desk.

OPENED PDF PAGE
---------------
Opening a cited PDF page now records that page as visible reading context.
The Ask area shows the opened citation and offers Ask from This Opened Page.
That action selects the exact document and page without changing the PDF.

CITED RESULT REUSE
------------------
After a successful local page search, Reuse the current cited search results is
selected automatically. Agent Fox receives those exact cited references instead
of launching a second overly literal search.

EXPLICIT PAGES
--------------
Page numbers written in the question are honored. The resolver filters selected
citations or recipe matches to that page. Missing pages fail immediately with a
specific failure code rather than silently falling back to an unrelated search.

RECIPES
-------
- Common question words such as make, prepare, find, and uses are removed before
  matching the named recipe.
- Quoted recipe names are honored.
- Nearby headings remain visible.
- Ingredient phrases remain classified as ingredient text, not recipe titles.
- Multiple matching recipes are counted and listed with their citations.
- A missing named recipe fails immediately and withholds ingredient-only hits.

FILES MODIFIED
--------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_BIBLIOTHECA_V1_2.py (new verifier)

PROTECTED
---------
- Controlled Research Desk and saved research
- Main FOXAI integration
- Kayock Writer and Poetry Studio
- Repair Bay
- Original PDFs and indexed database content
- Existing V1.6 verifier and current localhost-only behavior

No PDF, database record, saved research item, poem, story, model, or unrelated
FOXAI file is changed by this plan.

PLAN SHA-256
------------
11c1f21f62c059a0c7939b7f4bc1d8da35fb2ec51a293be59ddb31379b1b2c6c

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Bibliotheca_V1_2_Exact_Page_Recipe_Intelligence\BIBLIOTHECA_V1_2_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-030921-2A5D34
- Changed paths: 2
- Plan SHA-256: 11c1f21f62c059a0c7939b7f4bc1d8da35fb2ec51a293be59ddb31379b1b2c6c
