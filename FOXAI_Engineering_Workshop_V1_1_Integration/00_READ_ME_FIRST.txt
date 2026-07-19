FOXAI ENGINEERING WORKSHOP V1.1 — LIVE ENGINEER INTEGRATION

Purpose
-------
Connect the controlled Engineering Workshop worker to the live FOXAI
core/engineer_agent.py used by the Mission Console and WebUI.

What remains read-only
----------------------
Normal Engineer questions, searches, reviews, and investigations remain
read-only. The installer does not turn ordinary chat into automatic writes.

What becomes available
----------------------
Explicit /engineer workshop commands can stage a mission, locate live source,
save or preview an exact JSON plan, apply that exact plan after a SHA-256
confirmation, validate it, restore the snapshot automatically on failure, and
produce a tool-generated receipt.

Install
-------
1. Extract this ZIP to a normal folder.
2. Double-click INSTALL_ENGINEERING_WORKSHOP_V1_1.bat once.
   This is preview only and changes nothing.
3. Review the displayed target and file list.
4. Open a Command Prompt in the extracted folder and run:

   INSTALL_ENGINEERING_WORKSHOP_V1_1.bat --approve

5. Restart FOXAI WebUI.

First test in Mission Console
-----------------------------
/engineer workshop capabilities

Then:
/engineer workshop help

Safety
------
- Original source and Engineering files are backed up first.
- No deletion, rename, package install, or network action is performed.
- core/engineer_agent.py must match the verified GitHub anchors or installation
  stops before changing anything.
- Python compilation and Engineering Workshop fixture tests run after install.
- Any validation failure restores the backup automatically.
