BIBLIOTHECA V1.2.2 — SEARCH API RESPONSE RELIABILITY
Exact Engineering Workshop Plan

Mission:
ENG-20260720-043740-A65C3A

ROOT CAUSE
----------
The /api/search route copied every result field using strict dictionary access.
Ordinary PDF page results do not contain research-only fields such as:

- section_heading
- capture_date
- original_url

That raised KeyError before the server could return JSON, so the browser only
showed Failed to fetch.

THE REPAIR
----------
- Use the existing safe public_source serializer.
- Missing optional fields are returned as null instead of crashing.
- Recipe pages include detected_heading and match_role when available.
- Saved research segments retain their research metadata.
- Genuine endpoint failures return controlled JSON with error_code
  local_search_failed.
- Technical exception details are recorded in the local Bibliotheca log.
- Private project paths are not exposed in the browser error response.
- The interface replaces generic Failed to fetch wording with a useful local
  service message.

LIVE HTTP VERIFICATION
----------------------
The verifier starts an isolated Study server on a temporary loopback port and
checks:

- Nelson Family Recipe Book / White Bread: HTTP 200 and valid JSON
- Ordinary non-recipe PDF: HTTP 200 and valid JSON
- OCR recipe page: HTTP 200 and valid JSON
- Saved research segment: HTTP 200 and valid JSON
- No-results search: HTTP 200 with an empty result list
- Forced internal failure: HTTP 500 with controlled JSON and local logging

FILES MODIFIED
--------------
- KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py
- KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_BIBLIOTHECA_V1_2_2.py

PROTECTED
---------
- Bibliotheca V1.2 exact-page and recipe intelligence
- Bibliotheca V1.2.1 layout and Use This Recipe controls
- Controlled Research Desk
- Main FOXAI, Kayock Writer, Poetry Studio, and Repair Bay
- Original PDFs, indexed database content, and saved research

No external internet connection is used. The HTTP regression operates only on
127.0.0.1 inside a temporary isolated fixture.

PLAN SHA-256
------------
9200f623dfa4403b5e564863965ca03cd4ec2eca2d6cc46df3b6d6e5e286967a

NEXT STEP — PREVIEW ONLY
------------------------
Extract this complete folder directly inside Z:\FOXAI, then enter:

/engineer workshop preview "Z:\FOXAI\FOXAI_Bibliotheca_V1_2_2_Search_API_Reliability\BIBLIOTHECA_V1_2_2_EXACT_PLAN.json"

Expected:
- Mission ID: ENG-20260720-043740-A65C3A
- Changed paths: 2
- Plan SHA-256: 9200f623dfa4403b5e564863965ca03cd4ec2eca2d6cc46df3b6d6e5e286967a
