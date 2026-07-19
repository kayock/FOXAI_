KAYOCK'S STUDY V1.6 — CONTROLLED RESEARCH DESK R3 OCR-AWARE

Mission:
ENG-20260719-195102-AE63D3

R2 rollback cause:
The validation selected the first matching database record by ID. That can be
the original scanned/non-OCR copy, even when a searchable OCR copy exists.

R3 correction:
The regression test now considers every matching Nelson Family Recipe Book
page-7 record and prefers:
1. Searchable OCR copy
2. Searchable copy
3. Partially searchable copy
4. Low-text scan
5. Unreadable copy

Both the original scan and OCR copy remain preserved. No PDF is changed.

Simulation:
A low-ID non-OCR scan and a later OCR copy were placed in the test database.
R3 selected the OCR copy and passed all 31 checks.

PREVIEW
/engineer workshop preview "Z:\FOXAI\FOXAI_Kayocks_Study_V1_6_Controlled_Research_Desk_R3_OCR_Aware\KAYOCKS_STUDY_V1_6_R3_EXACT_PLAN.json"

Expected Plan SHA-256:
7bfe0aab04d1bc33c3a10fcb7f61512ec214c0b524475055c37706f19c8a5b2e
