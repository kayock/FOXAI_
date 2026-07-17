# FOXAI USB Commissioning Phase 1 — Exact Preview R2

## R1 result

R1 safely stopped fail-closed after all of these passed:

- package identity;
- locked live baselines;
- candidate identity and static safety checks;
- live no-write commissioning;
- READY / READY_WITH_NOTES / NEEDS_ATTENTION contract.

The no-write commissioner reported **READY_WITH_NOTES** overall.

The final Boundary Watch runner failed before executing the tests because it
used the module name `tests.test_boundary_watch`. The live `tests` directory
does not contain a package marker.

## R2 repair

R2 changes only `verify_preview.py` and package documentation/receipts.

The locked Boundary Watch suite is now invoked with:

`python -m unittest discover -s tests -p test_boundary_watch.py -v`

This preserves the live root on Python's import path and executes the same
five locked tests without requiring `tests` to be a package.

The verifier now also:

- locks `tests/test_boundary_watch.py` to its approved SHA-256;
- records the exact test file and hash;
- retains stdout, stderr, return code, and diagnostic tail on failure.

## Candidate scope

Candidate files remain byte-for-byte identical to R1:

- `COMMISSION_FOXAI_USB.bat`
- `System/Commissioning/commission_usb.py`
- `00_START_HERE/USB_COMMISSIONING_GUIDE.md`

Existing live files modified by the proposed milestone: **none**

Delete operations: **none**

Apply capability in this package: **none**
