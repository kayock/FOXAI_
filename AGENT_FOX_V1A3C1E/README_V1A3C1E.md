# Agent Fox Technical Core V1A-3C1E

Mission: `ENG-20260721-215917-186FD1`

This bounded reconciliation rebuilds only the already-proven Web Portable preliminary closure:

- `Z:/FOXAI/START_FOXAI_WEB_PORTABLE.bat`
- `Z:/FOXAI/env/python/python.exe`
- `Z:/FOXAI/core/foxai_web.py`
- 57 reached Python source files
- 165 static first-party dependency edges
- 1 unresolved branch

Each reached source is hashed at most once on active NTFS `Z:` and at most once on rollback `K:`. Files are streamed in 1 MiB chunks, below the 8 MiB buffer ceiling. The mission records whether each file is unchanged, evidence-stale, different between Z and K, missing, rollback-only, or missing an evidence record.

`K:` is read-only. The mission does not refresh immutable evidence, execute FOXAI application source, launch ComfyUI, load models, invoke a shell, use the network, or modify Hanger Bay, runtimes, packages, databases, source files, or the rollback drive.
