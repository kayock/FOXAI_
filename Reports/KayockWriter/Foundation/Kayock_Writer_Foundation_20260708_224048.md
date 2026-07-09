# Kayock Writer Foundation

Created: 2026-07-08T22:40:48
Milestone: **v10.11.0 Kayock Writer Foundation**
Health: **KAYOCK WRITER FOUNDATION READY**
Foundation ready: True
Read only: True
Report only: True

## Safety

- Read-only Kayock Writer foundation report.
- No story-file mutation.
- No rename performed.
- No migration performed.
- No overwrite.
- No delete.
- No install.
- No model cleanup.
- Future writes require explicit user approval.

## Summary

- Modules: 7
- Checks: 7
- Checks Passed: 7
- Problems: 0
- Naming Decisions: 5
- Path Checks: 6
- Existing Paths: 1
- Flagship Universe: Slipping into Darkness
- Foundation Ready: True
- Read Only: True
- Report Only: True

## Module Plan

### Story Forge
- ID: `story_forge`
- Status: `planned_foundation`
- Purpose: Novels, short stories, scripts, CYOA, scene drafting, chapter planning, and narrative development.
- Read only now: True
- Future writes: Story project Markdown and JSON files only, after explicit user action.

### Poetry Studio
- ID: `poetry_studio`
- Status: `planned_foundation`
- Purpose: Poem Creator and Poem Polisher for theme, emotion, poetic form, rhythm, imagery, line breaks, and preserving the writer voice.
- Read only now: True
- Future writes: Poetry drafts and polish reports only, after explicit user action.

### Codex
- ID: `codex`
- Status: `already_conceptualized`
- Purpose: Characters, lore, factions, artifacts, locations, prophecy, reader knowledge, author knowledge, and canon notes.
- Read only now: True
- Future writes: Codex entries only, after explicit user action.

### Timeline
- ID: `timeline`
- Status: `already_conceptualized`
- Purpose: Book, chapter, scene, flashback, prophecy, and cross-series chronology.
- Read only now: True
- Future writes: Timeline records only, after explicit user action.

### Continuity
- ID: `continuity`
- Status: `already_conceptualized`
- Purpose: Canon checks, contradiction tracking, unresolved setup/payoff tracking, and author memory.
- Read only now: True
- Future writes: Continuity reports only, after explicit user action.

### Mystery Tracker
- ID: `mystery_tracker`
- Status: `already_conceptualized`
- Purpose: Unresolved mysteries, clues, reveals, prophecy fragments, and payoff status.
- Read only now: True
- Future writes: Mystery tracker records only, after explicit user action.

### Story Bible Export
- ID: `story_bible_export`
- Status: `already_conceptualized`
- Purpose: Export a readable project bible from Codex, Timeline, Continuity, and project notes.
- Read only now: True
- Future writes: Exported story-bible Markdown only, after explicit user action.


## Naming Decisions

- `rename_novel_forge` — locked_in — Rename Novel Forge to Kayock Writer as the main creative writing department. Novel Forge becomes legacy/internal wording while Kayock Writer becomes the public department name.
- `story_forge_module` — locked_in — Use Story Forge as the narrative-writing module inside Kayock Writer. Story Forge covers novels, short stories, scripts, CYOA, narrative drafting, and scene/chapter work.
- `poetry_studio_module` — locked_in — Add Poetry Studio with Poem Creator and Poem Polisher. Poetry work supports creation and polishing while preserving the writer voice.
- `markdown_source_of_truth` — locked_in — Keep Markdown as the long-term portable source of truth. Future storage should remain portable, inspectable, and friendly to Obsidian or other tools.
- `provider_toggle` — planned — Preserve Local Mode and Cloud Mode as a future provider toggle. Local Mode for private canon/manuscripts; Cloud Mode for public-safe research and critique.

## Flagship Universe

- Title: Slipping into Darkness
- Status: flagship_demo_universe
- Book 1: Anthony learns the prophecy; Kayock dies; Jokaya kills him; Anthony stops Jokaya; Anthony learns his ex has been turned.
- Book 2: Anthony hunts the ex, learns who she has become, defeats her, discovers Jokaya sanctuary clues, follows Olmec/Croatoan/Crystal Skull threads.
- Use: Demonstration universe for Codex, Timeline, Continuity, Mystery Tracker, and Story Bible export.

## Path Checks

- `writer_department_root` — `Z:\FOXAI\Departments\KayockWriter` — exists: False — kind: missing
- `legacy_novel_forge_root` — `Z:\FOXAI\NovelForge` — exists: True — kind: folder
- `legacy_novel_forge_department` — `Z:\FOXAI\Departments\NovelForge` — exists: False — kind: missing
- `writer_projects_root` — `Z:\FOXAI\Projects\KayockWriter` — exists: False — kind: missing
- `writer_reports_root` — `Z:\FOXAI\Reports\KayockWriter` — exists: False — kind: missing
- `writer_foundation_reports` — `Z:\FOXAI\Reports\KayockWriter\Foundation` — exists: False — kind: missing

## Checks

- [PASS] `name_locked` — Kayock Writer is the selected department name.
- [PASS] `module_plan_present` — Core Kayock Writer module plan is present.
- [PASS] `poetry_studio_present` — Poetry Studio is included.
- [PASS] `story_forge_present` — Story Forge is included.
- [PASS] `codex_present` — Codex is included.
- [PASS] `flagship_universe_declared` — Flagship demo universe is declared.
- [PASS] `read_only_scope` — Foundation scope is read-only/report-only.

## Recommendations

- `start_kayock_writer_foundation` — Start Kayock Writer as the new creative writing foundation — Treat this as the beginning of v10.11.x. Keep Novel Forge as legacy wording while the interface transitions to Kayock Writer. — auto apply: False
- `next_story_forge_shell` — Build Story Forge Shell next — Create a read-only Story Forge overview with project list, scene/chapter plan, and future explicit-save workflow. — auto apply: False
- `poetry_studio_after_story_shell` — Add Poetry Studio after Story Forge shell — Add Poem Creator and Poem Polisher as separate cards after the writer foundation is stable. — auto apply: False
- `do_not_migrate_automatically` — Do not auto-migrate Novel Forge files — Any rename, folder creation, or migration should be a later explicit approved action with preview and backup. — auto apply: False