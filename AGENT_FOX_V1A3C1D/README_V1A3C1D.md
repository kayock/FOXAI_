# Agent Fox Technical Core V1A-3C1D

This isolated diagnostic reproduces the exact bounded Web Portable closure path that failed twice in mission `ENG-20260721-172935-37F095`—once on the original exFAT T7 and once on the internal NTFS test SSD.

It verifies and loads the exact prior V1A-3C1 builder, then runs its stages individually. Any exception is caught and recorded with its exact type, message, traceback, last successful stage, selected safe frame details, closure counters, source-read counters, and peak source bytes. The diagnostic command deliberately returns success after recording the failure so the Workshop retains the evidence rather than rolling it back.

No normal closure outputs are written. FOXAI source files are parsed statically but never imported or executed. No launchers, packages, models, ComfyUI components, child processes, shell commands, network operations, repairs, or changes to the rollback T7 on `K:` are used.
