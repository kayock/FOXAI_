KAYOCK'S STUDY — THE BIBLIOTHECA V1.3
Recipe Heading Retrieval Fix

PURPOSE

V1.2 correctly refused to invent a cooking time when it retrieved page 56,
but the retriever should not have selected that page first.

The page contained "white bread" only as an ingredient beneath:

  Kim's Ham & Broccoli Scallope

The real recipe titled White Bread was on page 7.

V1.3 fixes the selection stage before Agent Fox receives the sources.

NEW BEHAVIOR

For the Recipes shelf:

- Search matching pages broadly enough to inspect their detected headings.
- Rank exact recipe headings before related headings.
- Suppress ingredient-only matches when an exact or related title exists.
- Understand natural wording such as:
    How long does it take white bread to cook?
- Preserve ingredient-only pages for deliberate exact-page inspection.
- Keep multiple exact/related recipes separate and warn when needed.

For every other shelf:

- Existing V1.2 page grounding remains unchanged.
- Exact-page asking remains available.
- Reusing current cited results remains available.
- Model-offline handling remains fast and clear.

INSTALL

1. Close Kayock's Study and its black command window.
2. Extract this complete folder directly inside Z:\FOXAI.
3. Run:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1_3_RECIPE_HEADING_FIX\
   APPLY_BIBLIOTHECA_V1_3_RECIPE_HEADING_FIX.bat

4. Press Y.
5. Restart:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1\
   START_KAYOCKS_STUDY.bat

PRESERVATION

The installer requires the exact reviewed V1.2 server SHA-256.
It creates a verified server backup, a consistent SQLite snapshot, and a
receipt before replacing only:

  KAYOCKS_STUDY_BIBLIOTHECA_V1\study_server.py

It does not modify or delete PDFs, recipes, indexed pages, models, launchers,
the main FOXAI WebUI, or other Library shelves.

REQUIRED TEST

Select the Nelson Family Recipe Book and ask:

  How long does it take white bread to cook?

The selected source should be the page whose detected heading is White Bread,
not a page where "white bread" appears only in an ingredient list.
