Kayock Command OS v10.11.3 - Create Project Approval Gate

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
- Keeps v10.11.2 Story Project Manifest Preview.
- Adds Create Project Approval Gate page.
- Adds endpoint:
  POST /api/writer/create_project_gate

Approval Gate shows:
- Proposed project root
- Proposed manifest target
- Exact approval phrase
- Whether typed phrase matches
- Creation disabled in this build
- Proposed future writes
- Target existence checks
- Overwrite risk checks
- Parent folder expectations
- Legacy source files for future copy-only import
- Copy-only legacy import policy
- Checks
- Safety contract
- Export gate report
- Send gate report to Mission

Exports:
Z:\FOXAI\Reports\KayockWriter\CreateProjectGate\

Expected current result:
CREATE PROJECT APPROVAL GATE READY

Safety:
Gate preview only.
Read-only legacy scan.
No project creation.
No story-file mutation.
No legacy migration.
No rename performed.
No overwrite.
No delete.
No install.
No model cleanup.
Only optional gate export.
