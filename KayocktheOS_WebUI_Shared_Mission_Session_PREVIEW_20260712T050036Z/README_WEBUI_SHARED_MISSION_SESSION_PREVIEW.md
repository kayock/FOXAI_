# WebUI Shared Mission Session - Preview Only

## Safety state

This package is **preview only**. It contains no apply command and does not
modify live FOXAI files.

Extract the whole folder directly inside `Z:\FOXAI`, then run:

`PREVIEW_WEBUI_SHARED_MISSION_SESSION.bat`

A successful run must report `State: preview_ready` and
`NO LIVE FILES WERE MODIFIED.`

## Exact proposed live scope

Create:

- `core\mission_session.py`

Update:

- `core\foxai_web.py`

Explicitly untouched:

- `core\memory.py`
- `ui\main_window.py`
- `core_v10\*`
- `core\director.py`
- `core\engineer_agent.py`
- `core\security_containment.py`

## Proposed architecture

The WebUI keeps ordinary chat on its current local-model path. Only an explicit
`/engineer`, `Engineer:`, or `Engineer,` command enters the current Director and
Engineering Airlock.

The proposal does **not** connect the parallel `core_v10` MissionBus and does
not use the old `archive_chat_legacy()` helper.

A new interface-independent `MissionSession` owns one stable archive path for
all turns in a WebUI session. Each save uses a temporary file plus atomic
replace, reopens the file, compares the full transcript, and verifies SHA-256
before the WebUI may report the turn as successfully archived.

## Proposed routing behavior

- `/api/chat/start` creates a new WebUI mission session after chat health is verified.
- `/api/chat/reset` creates a fresh session.
- Changing project, professor, or model creates a new session.
- Ordinary text stays with Agent Fox or the selected professor.
- Explicit Engineer commands pass through current Director/Airlock authorization.
- Engineer is called through `analyze()` only; no Repair Chamber authority is added.
- Known Engineer project-memory write commands are denied by the WebUI read-only gate.
- Eric's message and the returned response are both archived.
- Archive verification controls the API `ok` result.
- The current model-action claim guard remains active.

## Proposed archive layout

`Mission Archive\Chats\YYYY\MM\DD\<time> WebUI Mission <id>.md`

The same file is atomically updated across multiple turns in the same session.

## Baseline hashes required by the preview

`core\foxai_web.py`

`4783a95fabb4e494aa8847bbc9eb6266ab5b9779d292ebcc789c945944252c43`

`core\engineer_agent.py`

`a533239c0e4d56352e2efe9ae0e42b1d00616300421da9222ca5e33091f11b8a`

## Candidate hashes

`core\foxai_web.py`

`0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda`

`core\mission_session.py`

`d1032abb31b30f9b5a0b8e6169983de368d4a5ab474438f454fe385436a6d57a`

## Verification completed while building this preview

- Candidate Python compilation: PASS
- MissionSession functional tests: 6 PASS
- WebUI routing/archive source tests: 11 PASS
- Phase 1 containment regression tests: 15 PASS
- Engineer intake regression tests: 8 PASS
- Stable archive path across turns: PASS
- Atomic-write failure cannot claim success: PASS
- Project-memory write commands denied in WebUI Engineer: PASS
- Exact diff generated: PASS
- Parallel `core_v10` integration added: NO
- Legacy archive helper added: NO
- Live FOXAI files modified: NO

## Risks reserved for the later apply smoke test

- The first WebUI Engineer request may take slightly longer while Engineer loads lazily.
- The WebUI still has its existing process-global chat state; this milestone does not
  redesign multi-browser concurrency.
- If archive storage is unavailable, the answer may be displayed with an error, but
  the API must return `ok: false` and cannot claim the archive succeeded.
- A later apply bundle must verify a real portable-Python WebUI server, an explicit
  Engineer request, ordinary model chat, archive read-back, backup, and rollback.

## Review files

- `WEBUI_SHARED_MISSION_SESSION_EXACT.diff` - exact proposed source changes
- `PREVIEW_BUNDLE_VERIFICATION_RECEIPT.json` - build-time tests and hashes
- `candidate\core\mission_session.py` - proposed new archive service
- `candidate\core\foxai_web.py` - proposed WebUI integration
