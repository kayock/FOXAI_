KAYOCK'S STUDY — THE BIBLIOTHECA V1.5
Live Model Status and Exact Citation Labels

WHAT V1.5 FIXES

1. LIVE MODEL STATUS

Bibliotheca previously learned that the local model had started only when the
whole page was refreshed.

V1.5 checks the localhost model every 2.5 seconds and updates the status badge
without reloading the Study. Returning to the browser tab also triggers an
immediate check.

This polling stays entirely on:

  127.0.0.1

It does not access the public internet.

2. EXACT CITATION LABELS

Agent Fox previously produced a correct page number but wrote the placeholder:

  [Document Title, p. 7]

V1.5 supplies the exact allowed citation labels to the model, tells it never
to use placeholders, and safely normalizes a placeholder only when that page
maps to one unambiguous retrieved document.

For example:

  [Nelson Family Recipe Book, p. 7]

When a placeholder cannot be resolved safely, Bibliotheca leaves it unchanged
and displays a citation warning instead of guessing.

INSTALL

1. Close Kayock's Study and its black command window.
2. Extract this complete folder directly inside Z:\FOXAI.
3. Run:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1_5_LIVE_MODEL_CITATION_FIX\
   APPLY_BIBLIOTHECA_V1_5_LIVE_MODEL_CITATION_FIX.bat

4. Press Y.
5. Restart:

   Z:\FOXAI\KAYOCKS_STUDY_BIBLIOTHECA_V1\
   START_KAYOCKS_STUDY.bat

No reindex is needed.

QUICK TESTS

Model status:
- Start Bibliotheca while the model is off.
- Start the FOXAI model.
- The badge should change to Local model online within about 2.5 seconds
  without refreshing the page.

Citation:
- Ask the White Bread cooking-time question again.
- The answer should use the actual retrieved document title and page,
  not [Document Title, p. 7].

PRESERVATION

The installer requires the exact reviewed V1.4 server SHA-256.
It creates a verified server backup, a consistent SQLite snapshot, and a
receipt before replacing only:

  KAYOCKS_STUDY_BIBLIOTHECA_V1\study_server.py

It does not alter or delete PDFs, recipes, indexed pages, models, launchers,
the main FOXAI WebUI, or any other Library shelf.
