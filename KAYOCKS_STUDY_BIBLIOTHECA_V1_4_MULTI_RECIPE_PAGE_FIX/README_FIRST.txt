KAYOCK'S STUDY — THE BIBLIOTHECA V1.4
Multi-Recipe Page Grounding Fix

WHY THIS FIX EXISTS

The real Nelson Family Recipe Book exposed a flaw that the synthetic V1.3
test did not reproduce closely enough.

Page 7 contains several recipes. The PDF text extractor can merge a recipe
title with its author line or split the title across lines. V1.3 failed to
recognize White Bread as a title and fell back to ordinary word search,
returning pages where "white bread" appeared only as an ingredient.

V1.4 fixes that behavior.

NEW RULES

For the Recipes shelf:

- Recover a named recipe title when PDF extraction merges it with an author
  line, for example:
    White Bread Olive Jacobson--recipe from her mom...
- Recover a title split across two or three nearby extracted lines.
- Reject ingredient lines such as:
    1 cup white bread, crumbled
    8 cups white bread flour
  as recipe titles.
- For cooking-time, temperature, preparation, or instruction questions,
  require a recipe-heading match before returning sources.
- When no matching recipe heading is found, show a clear message and withhold
  unrelated ingredient-only pages.
- Exact-page asking still permits deliberate inspection of any page.

Other shelves retain normal V1.3 grounding behavior.

INSTALL

1. Close Kayock's Study and its black command window.
2. Extract this complete folder directly inside Z:\FOXAI.
3. Run:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1_4_MULTI_RECIPE_PAGE_FIX\
   APPLY_BIBLIOTHECA_V1_4_MULTI_RECIPE_PAGE_FIX.bat

4. Press Y.
5. Restart the existing Study:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1\
   START_KAYOCKS_STUDY.bat

REQUIRED REAL TEST

Select the Nelson Family Recipe Book and ask:

  How long does it take white bread to cook?

The first retrieved source must have:

  Heading: White Bread

Ingredient-only pages such as Ham Balls, Whole Wheat Bread ingredients,
Caramel Buns, or Noodle Casserole must not be offered as recipe-title matches.

PRESERVATION

The installer requires the exact reviewed V1.3 server SHA-256.
It creates a verified V1.3 server backup, a consistent SQLite snapshot, and
an upgrade receipt before replacing only study_server.py.

It does not modify or delete PDFs, recipes, indexed pages, models, launchers,
the main FOXAI WebUI, or any other shelf.
