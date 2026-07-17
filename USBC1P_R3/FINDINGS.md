# FOXAI USB Commissioning Phase 1 — Exact Preview R3

## R2 result

R2 safely stopped fail-closed. The following all passed:

- package manifest;
- approved live baselines;
- unchanged candidate identity;
- Python compilation and static safety checks;
- live no-write commissioning;
- READY / READY_WITH_NOTES / NEEDS_ATTENTION reporting.

The live no-write commissioner again reported **READY_WITH_NOTES** overall.

The final test process discovered `test_boundary_watch.py`, but the bundled
embeddable Python could not import `core.security_containment`.

## Cause

`env/python/python314._pth` places embedded Python in an isolated search-path
mode. Its `.` entry is resolved beside `python.exe`, not from the command's
working directory. Therefore `cwd=Z:\FOXAI` does not itself expose the FOXAI
root for imports.

## R3 correction

R3 changes only the preview verifier and package documentation/receipts.

The verifier launches the bundled Python with a small in-memory runner that:

1. receives the resolved FOXAI root as an argument;
2. inserts that root at the front of `sys.path`;
3. discovers only `tests/test_boundary_watch.py`;
4. runs the same locked five tests;
5. returns failure unless all five pass.

No environment variable, installed package, writable helper script, or live
source modification is used.

## Candidate scope

Proposed additions remain byte-for-byte identical:

- `COMMISSION_FOXAI_USB.bat`
- `System/Commissioning/commission_usb.py`
- `00_START_HERE/USB_COMMISSIONING_GUIDE.md`

Modified existing live files: **none**

Deleted live files: **none**

Apply capability: **absent**
