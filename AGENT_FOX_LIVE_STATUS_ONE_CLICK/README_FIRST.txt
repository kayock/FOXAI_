FOXAI AGENT FOX LIVE STATUS — ONE CLICK

1. Close FOXAI WebUI.
2. Extract this folder directly into Z:\FOXAI.
3. Open Z:\FOXAI\AGENT_FOX_LIVE_STATUS_ONE_CLICK.
4. Double-click INSTALL_AGENT_FOX_LIVE_STATUS.bat.
5. Start FOXAI WebUI normally.

No PowerShell and no Engineering Workshop command.

Normal WebUI chat will answer these from live read-only evidence:

What Python is FOXAI using?
How much free space is on Z:?
Is ComfyUI running?
Which FOXAI launchers are active?
What model is loaded?
Show me FOXAI's current status.

The answers are captured from the current WebUI process, current drive reading,
localhost health checks, current model state, and the current process list.

Historical mission receipts are not substituted for a live reading.

The model prompt is also corrected so owner-local read-only details are not
described as "not publicly disclosed," confidential, or restricted. If live
evidence is unavailable, Agent Fox must say it is unavailable rather than guess.

This installer changes only:

Z:\FOXAI\core\foxai_web.py

It creates a backup and automatically restores the original if compilation or
the focused six-question tests fail.

Explicit slash commands, Engineer, Workshop, Casbin, Red Canvas, exact-file
grounding, and destructive-action confirmation are unchanged.
