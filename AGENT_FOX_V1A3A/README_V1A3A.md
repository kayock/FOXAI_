# Agent Fox Technical Core V1A-3A

Mission: `ENG-20260721-071125-0FB108`

This isolated component builds a bounded Python Runtime Identity and Path Safety Map.

It may execute at most four exact `python.exe` files, one at a time, with `-I -B -S -c`, a 15-second timeout, `shell=False`, and standard-library-only identity code. Missing, failed, denied, timed-out, and malformed probes become evidence rather than broad retries.

It never executes `pythonw.exe`, FOXAI application source, launchers, models, Llama, ComfyUI, PowerShell scripts, services, tasks, or repairs. It does not invoke pip or import third-party packages.

Static package evidence is derived from metadata, `top_level.txt`, `RECORD` names, direct top-level entries, `.pth`, `._pth`, and `pyvenv.cfg`. Duplicate modules and versions are reported as candidates, never as proof of an active conflict.
