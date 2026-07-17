FOXAI Portable Desktop Runtime Phase 3A — Read-Only Audit

The audit automatically checks Desktop shortcuts with names containing
FOXAI, Fox AI, Kayock, or Agent Fox. It records only their launch metadata:
target, arguments, working directory, icon, and description.

It also inspects:

- Start FoxAI and related FOXAI/Kayock root launchers
- ui\main_window.py imports and path assumptions
- env\python
- .venv
- discovered system Python installations
- Tcl/Tk availability without opening a GUI
- CustomTkinter, Pillow, psutil, requests, Casbin, Watchdog, and Pluggy
- reusable packages in Runtime\Core
- the safest Phase 3B portable Desktop-runtime design

It does not open FOXAI Desktop, invoke pip, install packages, access the
network, change shortcuts, or modify any live file.

Extract PDR3A directly into:

  Z:\FOXAI\PDR3A\

First run:

  Z:\FOXAI\PDR3A\VERIFY_PACKAGE.bat

Expected:

  State: desktop_runtime_audit_package_verified
  Verified: True
  Apply capability present: False
  Live files modified: False
  Desktop GUI launched: False

Then run:

  Z:\FOXAI\PDR3A\RUN_DESKTOP_RUNTIME_AUDIT.bat

Upload the single archive printed by the audit:

  Z:\FOXAI\Reports\DesktopRuntimeAudit\
  PDR3A_<timestamp>\PDR3A_RESULTS.zip

If no matching shortcut is found, no harm is done. We will then only need
the shortcut's Target and Start-in values before Phase 3B.
