Kayock Command OS v10.14.9 - Chapter Prose Continue Refresh / Compare

Install:
1. Backup:
   Z:\FOXAI\core\foxai_web.py

2. Copy:
   core\foxai_web.py
   over:
   Z:\FOXAI\core\foxai_web.py

3. Run:
   START_FOXAI_WEB_PORTABLE.bat

What this adds:
- New page: Prose Continue Verify.
- New endpoint: /api/writer/chapter_prose_continue_refresh_compare.
- Read-only verification that v005 exists after v10.14.8.
- Verifies v005 draft, metadata, and evidence files.
- Verifies v005 hash and word count.
- Confirms v005 continues from v004.
- Confirms v005 previous_draft_hash matches the v004 hash.
- Compares v004 → v005 with added/removed lines and unified diff.
- Confirms the Private Human Screen was not used, received, stored, echoed, or included.

Test:
Prose Continue Verify
→ Book 2
→ Chapter 2
→ From: 4
→ To: 5
→ Load Continue Verify
→ Export Continue Verify

Expected:
CHAPTER PROSE CONTINUE REFRESH COMPARE READY
Checks passed: 25/25
Problems: 0

Safety:
Read-only verification.
No draft save.
No chapter-file edit.
No story-file mutation.
No overwrite.
No delete.
No move.
No install.
No model cleanup.
Private Human Screen text is not sent to this endpoint by the UI.
