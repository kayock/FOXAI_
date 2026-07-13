# Engineer Intake & SmartSearch Repair — Preview

This is the prerequisite repair before Engineer can reliably prepare structured
Repair Chamber proposals.

The desktop UI correctly authorizes `/engineer`, but Engineer currently receives
the entire operator command. Its SmartSearch branch also bypasses its existing
target parser and sends the whole command to Kernel search.

## Proposed live change

Only:

`core\engineer_agent.py`

No repair is applied by this preview. Engineer remains read-only.

## Expected behavior after the proposed change

- `/engineer smart search for COMFY_MAIN` searches for `COMFY_MAIN`.
- `/engineer smart search for "launch(pycmd()"` searches for `launch(pycmd()`.
- `Engineer:` and `Engineer,` prefixes are normalized.
- `What do engineers do?` is preserved as ordinary text.
- Empty search targets return a safe read-only usage message.
- Existing SmartSearch source-first, vendor-exclusion, protected-path, and
  secret-redaction behavior remains in force.

## Verification already completed

- Phase 1 Engineer baseline SHA-256: `bf32b0ab80b6cc3a177698101a5c2121a4224d0bf55bbe78c047f541fb3a6339`
- Candidate SHA-256: `a533239c0e4d56352e2efe9ae0e42b1d00616300421da9222ca5e33091f11b8a`
- Python compilation: PASS
- Targeted unit tests: 8 PASS
- Live FOXAI files changed: NO

## USB preview

Extract this folder into its own folder inside `Z:\FOXAI`, then run:

`PREVIEW_ENGINEER_INTAKE_REPAIR.bat`

A successful preview must show `State: preview_ready` and
`Modified live files: NO`.
