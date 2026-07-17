FOXAI Portable Desktop Runtime Phase 3B — Exact Design

Protected stable Desktop chain:

  Launch FOXAI Workshop.bat - Shortcut.lnk
    -> Launch FOXAI Workshop.bat
    -> foxai.py

Protected WebUI chain:

  START_FOXAI_WEB_PORTABLE.bat - Shortcut.lnk
    -> START_FOXAI_WEB_PORTABLE.bat

Both shortcuts use USB-owned icons under Z:\FOXAI\Icons.

Phase 3B inspects the exact `python` command used by the stable launcher,
parses the recursive local Desktop dependency closure, records package and
Tcl/Tk requirements, and writes the exact proposed portable-runtime layout.

It does not launch FOXAI, use the network, run pip, install packages,
or change either shortcut, launcher, source file, model, or runtime.

Extract PDR3B directly into:

  Z:\FOXAI\PDR3B\

First run:

  Z:\FOXAI\PDR3B\VERIFY_PACKAGE.bat

Expected:

  State: desktop_runtime_design_package_verified
  Verified: True
  Apply capability present: False
  Live files modified: False

Then run:

  Z:\FOXAI\PDR3B\RUN_EXACT_DESIGN.bat

Upload:

  Z:\FOXAI\Reports\DesktopRuntimeDesign\
  PDR3B_<timestamp>\PDR3B_RESULTS.zip

The next step is Phase 3C: quarantined acquisition of a complete
USB-owned CPython/Tcl-Tk runtime and exact Desktop wheels.
