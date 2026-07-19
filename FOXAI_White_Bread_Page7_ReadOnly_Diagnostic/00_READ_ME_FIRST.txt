WHITE BREAD PAGE-7 READ-ONLY DIAGNOSTIC

This diagnostic opens the Bibliotheca SQLite database in read-only mode.

It does not:
- modify the database;
- modify or open the PDF;
- start the model;
- use the network;
- install anything;
- change FOXAI source.

Run:
RUN_WHITE_BREAD_PAGE7_DIAGNOSTIC.bat

It creates:
WHITE_BREAD_PAGE7_DIAGNOSTIC.json

Upload that JSON file into the ChatGPT conversation. It will reveal exactly how
the live PDF page text stores the temperatures and times, so the regression can
test the real extraction instead of guessing.
