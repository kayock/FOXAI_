# WebUI Shared Mission Session — Approved Apply Bundle

This bundle contains the exact candidate reviewed in the verified preview. It
does not change files merely by being extracted.

## Before running

1. Extract this folder directly inside `Z:\FOXAI`.
2. Close the console window opened by `START_FOXAI_WEB.bat`.
3. Do not run an older WebUI patch script.
4. Run `APPLY_WEBUI_SHARED_MISSION_SESSION.bat`.
5. At the local approval gate, type exactly:

`APPLY WEBUI SHARED MISSION SESSION`

## Approved live scope

Update:

- `core\foxai_web.py`

Create:

- `core\mission_session.py`

Explicitly unchanged:

- `core\memory.py`
- `ui\main_window.py`
- `core_v10\*`
- `core\director.py`
- `core\engineer_agent.py`
- `core\security_containment.py`

## What the installer does

- Requires the exact reviewed WebUI and Engineer baseline hashes.
- Refuses to run while port 8765 indicates the WebUI server is active.
- Requires the exact local approval phrase.
- Creates and verifies a rollback backup before modification.
- Installs `mission_session.py` before the WebUI that imports it.
- Uses atomic replacement for both files.
- Compiles both installed files with FOXAI portable Python.
- Runs 6 MissionSession tests.
- Runs 11 WebUI routing/archive tests.
- Runs 15 Phase 1 containment tests.
- Runs 8 Engineer intake tests.
- Starts the installed WebUI Handler on an ephemeral local port.
- Uses a deterministic local chat-API fixture to verify ordinary Agent Fox chat.
- Verifies the model-action claim guard through real HTTP.
- Sends a real HTTP `/engineer smart search for COMFY_MAIN` request.
- Verifies WebUI Engineer project-memory write denial.
- Reopens and checks one stable multi-turn archive.
- Keeps smoke-test archives inside the backup verification sandbox, not your real archive.
- Automatically restores the exact pre-apply state if any verification fails.

## Reviewed hashes

Baseline `core\foxai_web.py`:

`4783a95fabb4e494aa8847bbc9eb6266ab5b9779d292ebcc789c945944252c43`

Required current `core\engineer_agent.py`:

`a533239c0e4d56352e2efe9ae0e42b1d00616300421da9222ca5e33091f11b8a`

Candidate `core\foxai_web.py`:

`0a20f4988f3798aa60eab424ed1cba656b780bde5b131624ee959aa16c824bda`

Candidate `core\mission_session.py`:

`d1032abb31b30f9b5a0b8e6169983de368d4a5ab474438f454fe385436a6d57a`

Approved exact diff:

`334198bc2289929cb56cd77ebc66cacdad1b40c5f9d84068f15a31a163a2a5b1`

Uploaded verified preview receipt:

`ac1c7a5fc9b34029dd5f283df76e42f791164cf7edd21bd3736e6f34c047e20c`

## Success message

A complete success ends with:

`WEBUI SHARED MISSION SESSION APPLIED AND VERIFIED`

The receipt is written under:

`Z:\FOXAI\Reports\SecurityMilestone\WebUISharedMission_Apply_Receipt_<timestamp>.json`

## Manual rollback

Close the WebUI server and run:

`ROLLBACK_WEBUI_SHARED_MISSION_SESSION.bat`

Then type:

`ROLLBACK WEBUI SHARED MISSION SESSION`

The rollback tool verifies the preserved candidate and the selected backup before
restoring anything.
