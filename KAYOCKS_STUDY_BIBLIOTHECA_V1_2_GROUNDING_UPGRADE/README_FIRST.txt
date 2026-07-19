KAYOCK'S STUDY — THE BIBLIOTHECA V1.2
Grounded Page Questions

PURPOSE

V1.2 fixes the grounding problem exposed when the words "white bread flour"
on the Whole Wheat Bread page were mistaken for a recipe titled White Bread.

CITATIONS ARE NOT ENOUGH BY THEMSELVES

V1.2 now checks what the cited words refer to before Agent Fox answers.

NEW FEATURES

- Exact-page input in Ask Agent Fox
- "Ask from this page" on every search result
- "Ask from These Cited Pages" reuses the current retrieved results
- Explicit phrases such as "page 7" are honored when one document is selected
- Recipe-heading detection
- Recipe titles are separated from ingredient wording
- A named recipe is preferred over pages where its words occur only in ingredients
- Multiple matching recipe headings produce a visible warning
- Agent Fox is instructed to keep different recipes and instructions separate
- General books receive a simpler fallback query when natural questions are
  too strict for the page-search engine
- Offline model checks fail quickly
- Retrieved cited pages remain visible when the model is unavailable
- The local-model request timeout is reduced from five minutes to two minutes

OTHER BOOKS

Recipe-specific heading rules apply only to the Recipes shelf.
Manuals, RPG books, poetry, fiction, and other shelves retain normal page
grounding. Exact-page asking and reuse of cited results work for every shelf.

INSTALL

1. Close Kayock's Study and its black command window.
2. Extract this complete folder directly inside Z:\FOXAI.
3. Run:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1_2_GROUNDING_UPGRADE\
   APPLY_BIBLIOTHECA_V1_2_UPGRADE.bat

4. Press Y.
5. Restart the existing Study:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1\
   START_KAYOCKS_STUDY.bat

The address remains:

  http://127.0.0.1:8777

PRESERVATION

The installer requires the exact reviewed V1.1 server hash.
It creates:

- a verified V1.1 server backup
- a consistent SQLite database snapshot
- an upgrade receipt

It replaces only:

  KAYOCKS_STUDY_BIBLIOTHECA_V1\study_server.py

It does not alter or delete PDFs, indexed pages, recipes, receipts, models,
runtimes, launchers, or FOXAI's main WebUI.

WHITE BREAD TEST

After installation:

1. Search for: white bread
2. Press "Ask from this page" on page 7, or select the cookbook and enter 7
   in Exact page.
3. Ask: white bread bake time

V1.2 should identify the heading White Bread on page 7.

If page 6 is deliberately selected, V1.2 should warn that "white bread"
appears as ingredient wording beneath the nearby heading Whole Wheat Bread.
