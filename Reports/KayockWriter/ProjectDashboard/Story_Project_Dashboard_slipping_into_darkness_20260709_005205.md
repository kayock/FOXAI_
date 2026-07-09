# Kayock Writer Story Project Reader / Dashboard

Created: 2026-07-09T00:52:05
Milestone: **v10.11.5 Story Project Reader / Dashboard**
Health: **STORY PROJECT DASHBOARD READY**
Dashboard ready: True
Project: **Slipping into Darkness**

## Safety

- Read-only project dashboard.
- No story-file mutation.
- No project creation.
- No legacy migration.
- No rename performed.
- No overwrite.
- No delete.
- No move.
- No install.
- No model cleanup.

## Summary

- Project Id: slipping_into_darkness
- Title: Slipping into Darkness
- Project Root: Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness
- Project Exists: True
- Required Folders: 10
- Required Folders Ok: 10
- Manifest Exists: True
- Manifest Valid: True
- Manifest Status: active_project
- Readme Exists: True
- Books Outline Exists: True
- Source Files: 7
- Source Json: 3
- Source Markdown: 3
- Source Text: 1
- Source Bytes: 86965
- Expected Sources: 7
- Expected Sources Ok: 7
- Books In Manifest: 2
- Checks: 10
- Checks Passed: 10
- Problems: 0
- Dashboard Ready: True
- Read Only: True
- Report Only: True

## Manifest Summary

- api_version: kayock.writer.project.v1
- project_id: slipping_into_darkness
- title: Slipping into Darkness
- department: Kayock Writer
- module: Story Forge
- status: active_project
- storage: Markdown source of truth with JSON sidecars where useful
- books: `[{"id": "book_1", "title": "Book 1", "status": "outline_seed", "summary": "Anthony learns the prophecy; Kayock dies; Jokaya kills him; Anthony stops Jokaya; Anthony learns his ex has been turned.", "chapter_placeholder_count": 0, "scene_placeholder_count": 0}, {"id": "book_2", "title": "Book 2", "status": "outline_seed", "summary": "Anthony hunts the ex, learns who she has become, defeats her, discovers Jokaya sanctuary clues, follows Olmec/Croatoan/Crystal Skull threads.", "chapter_placeholder_count": 0, "scene_placeholder_count": 0}]`
- handoff_points: `{"codex": ["characters", "locations", "artifacts", "prophecy", "factions", "reader knowledge", "author knowledge"], "timeline": ["book chronology", "chapter chronology", "flashbacks", "prophecy timing", "ancient-history threads"], "continuity": ["canon checks", "contradiction flags", "setup/payoff", "unresolved mystery links"], "mystery_tracker": ["clues", "reveals", "prophecy fragments", "Crystal Skulls", "Croatoan trail", "Jokaya sanctuary"]}`
- provider_mode_plan: `{"local_mode": "Private canon, lore, manuscript, and story-bible work.", "cloud_mode": "Public-safe research, trope review, pacing critique, and fresh-eyes feedback."}`
- safety_contract: `{"legacy_import_copy_only": true, "no_delete": true, "no_move": true, "no_overwrite_without_backup": true, "future_story_writes_require_user_approval": true}`

## Folder Checks

- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness`
- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness\Source`
- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness\Markdown`
- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness\Chapters`
- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness\Scenes`
- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness\Codex`
- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness\Timeline`
- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness\Continuity`
- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness\Mysteries`
- [PASS] `Z:\FOXAI\Projects\KayockWriter\Slipping_into_Darkness\Exports`

## Source Files

- `Slipping.json` — .json — 2422 bytes
- `Slipping.md` — .md — 2245 bytes
- `Slipping_into_Darkness.json` — .json — 9063 bytes
- `Slipping_into_Darkness.md` — .md — 8668 bytes
- `Slipping_into_Darkness_Story_Bible_20260707_172721.json` — .json — 27419 bytes
- `Slipping_into_Darkness_Story_Bible_20260707_172721.md` — .md — 18576 bytes
- `Slipping_into_Darkness_Story_Bible_20260707_172721.txt` — .txt — 18572 bytes

## Checks

- [PASS] `project_root_exists` — Project root exists.
- [PASS] `required_folders_exist` — 10/10 required folders exist.
- [PASS] `manifest_exists` — project.kayock-writer.json exists.
- [PASS] `manifest_valid_json` — Manifest JSON parsed.
- [PASS] `manifest_active_project` — Manifest status is active_project.
- [PASS] `readme_exists` — README.md exists.
- [PASS] `books_outline_exists` — Markdown/Books.md exists.
- [PASS] `source_files_present` — Source files present: 7.
- [PASS] `expected_sources_exist` — 7/7 expected source copies exist.
- [PASS] `read_only_dashboard` — Project dashboard performed read-only inspection only.

## Recommendations

- `mark_project_dashboard_proven` — Mark Story Project Reader / Dashboard proven — Use this dashboard as the read-only proof that the created Story Forge project is usable. — auto apply: False
- `next_project_health_card` — Add Story Project card to Story Forge — Add a compact project health card directly to Story Forge so the project status is visible immediately. — auto apply: False
- `then_chapter_planner_preview` — Add Chapter Planner Preview — After the dashboard is stable, add a preview-only chapter card generator with no writes. — auto apply: False
- `keep_project_writes_gated` — Keep project writes gated — All future story files should use preview, no-overwrite checks, and explicit approval. — auto apply: False