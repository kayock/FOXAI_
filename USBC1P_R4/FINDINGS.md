# FOXAI USB Commissioning Phase 1 — Exact Preview R4

R3 stopped fail-closed after all package, baseline, candidate, static-safety, and no-write commissioning checks passed. Its Boundary Watch subprocess received literal backslash-n sequences and produced a syntax error before tests ran.

R4 changes only the preview verifier and package records. It uses one semicolon-separated Python command, explicitly inserts the FOXAI root into sys.path, discovers only tests/test_boundary_watch.py, and fails unless all five locked tests pass.

Candidate additions remain byte-for-byte identical:

- COMMISSION_FOXAI_USB.bat
- System/Commissioning/commission_usb.py
- 00_START_HERE/USB_COMMISSIONING_GUIDE.md

Modified existing live files: none

Deleted live files: none

Apply capability: absent
