# FOXAI Phase 3B-R2-FIX1

This replaces the earlier R2 package, which contained a PowerShell report-formatting parser error.

The failure was not caused by the folder or file name being too long. A PowerShell backtick immediately before a closing double quote escaped that quote, so PowerShell treated later lines as part of one unfinished string.

## Run

1. Extract this short-named folder inside `Z:\FOXAI`.
2. Double-click `RUN_USB_ROOT_SHORTCUT_CONTRACT_PROBE.bat`.
3. Zip and upload the newest folder created under `probe_output`.

## Safety

The probe is still read-only. It does not create or edit shortcuts, launch FOXAI, install packages, access the network, or change live FOXAI files. Phase 3C remains blocked.
