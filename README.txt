Kayock Command OS v10.12.2 - Chapter Editor Preview

Install:
1. Backup:
   Z:\FOXAI\core\foxai_web.py

2. Copy:
   core\foxai_web.py
   over:
   Z:\FOXAI\core\foxai_web.py

3. Run:
   START_FOXAI_WEB_PORTABLE.bat

What changed:
- Keeps v10.12.1 Saved Chapter Health Card.
- Adds Chapter Editor Preview page.
- Adds endpoint:
  POST /api/writer/chapter_editor_preview

Chapter Editor Preview reads:
- selected saved Markdown chapter card
- title and metadata
- goal / conflict / reveal / hook
- continuity notes
- handoff tags JSON
- draft space
- safety notes

Editor preview modes:
- Load Editor Preview: reads saved Markdown into fields.
- Preview Unsaved Changes: compares typed field changes against current file content.
- Export Editor Preview: writes report only.

Exports:
Z:\FOXAI\Reports\KayockWriter\ChapterEditorPreview\

Expected current result for Book 2:
CHAPTER EDITOR PREVIEW READY

Safety:
Read-only chapter editor preview.
No chapter file edit.
No story-file mutation.
No project creation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No move.
No install.
No model cleanup.
Only optional preview export.
