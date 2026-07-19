KAYOCK'S STUDY V1.6 — CONTROLLED RESEARCH DESK
Exact Engineering Workshop Plan

Mission:
ENG-20260719-195102-AE63D3

This package contains an exact JSON plan. It does not directly change FOXAI.
Engineering Workshop must preview the plan first and will create its own
targeted snapshot before applying it.

FILES CHANGED
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/START_KAYOCKS_STUDY.bat
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY.bat
- core/foxai_web.py

FILES ADDED
- KAYOCKS_STUDY_BIBLIOTHECA_V1/research_desk.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V1_6.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/Fixtures/research_article.html

PLAN SHA-256
5af670dfebccd4eb6a88fe99f79b635233550fbfa4f8692840491c2d36b43a65

NEXT STEP — PREVIEW ONLY
After extracting this complete folder directly inside Z:\FOXAI, enter this in
the FOXAI Mission Console:

/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V1_6_Controlled_Research_Desk_Plan\KAYOCKS_STUDY_V1_6_EXACT_PLAN.json"

Do not apply until the Workshop preview reports:
- Mission ID ENG-20260719-195102-AE63D3
- exactly 7 changed paths
- a Plan SHA-256 matching the value above
- no deletions or renames

The Workshop preview will provide the exact apply command. Use that command only
after reviewing the preview.

VALIDATION INCLUDED IN THE PLAN
1. Compile every changed Python source.
2. Run the existing isolated Kayock's Study environment verification.
3. Run the V1.6 offline fixture, preservation, duplicate, revision, Research
   shelf, citation, WebUI deep-link, and White Bread page-7 regression checks.

NETWORK AND PACKAGE RULES
- No network is used during validation.
- No package is installed.
- No PDF is modified, moved, renamed, or deleted.
- The first live web retrieval remains an explicit operator action after the
  completed interface is opened.
