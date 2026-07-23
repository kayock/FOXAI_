# Agent Fox Technical Core V1A-3C3

Mission: `ENG-20260721-224437-0FDDE1`

This mission builds one bounded static first-party dependency closure for the Workshop ComfyUI manager helper context:

- `Z:\FOXAI\Launch FOXAI Workshop.bat` at line 12
- `Z:\FOXAI\Runtime\Desktop\python\python.exe` with flags `-I -B -S`
- `Z:\FOXAI\System\PortableRuntime\manage_comfyui_normal.py` with arguments `--root Z:\FOXAI spawn --source workshop`
- context `CTX-EEC78B5B382B239D`
- path group `PATHGROUP-25300F3FBF74CEEB`

Verified preliminary topology from immutable evidence:

- 1 reached first-party source
- 0 first-party dependency edges
- 1 preliminary unresolved branch: `psutil` at line 190

The same launcher also contains the separate pending `Z:\FOXAI\foxai.py` context `CTX-68030A15EE97A526` at line 24.
That context is recorded only as a related pending direct context. It is not merged, built, expanded, or included in this closure.

The builder inherits the explicit-None zero-byte-safe size verification proven in V1A-3C1-R1. It reads only reached
first-party source files, each at most once, does not start or stop ComfyUI, executes no FOXAI source or imports,
creates no child processes, uses no network, and never accesses rollback drive K:.
