PROJECT FORGE PREVIEW 8 — CODE SLICER INTEGRATION
=================================================

Purpose
-------
This clean preview integrates the exact approved Code Slicer V1 as Project Forge's
surgical source-reading layer for the Dirty Python Lab / native OpenCode pilot.

Preview 7 is not installed, imported, or run.

Start
-----
Double-click:
  START_PROJECT_FORGE_PREVIEW8.bat

The controller opens a large-print local browser page at:
  http://127.0.0.1:8788/

Safety architecture
-------------------
1. The original Dirty Python Lab is hashed and copied into a new disposable workspace.
2. Git creates a baseline snapshot in the disposable copy.
3. Exact Code Slicer V1 maps dirty_python_lab.py and extracts selected symbols.
4. OpenCode runs in a separate agent-view Git folder.
5. The full dirty_python_lab.py is physically absent from that agent view.
6. External-directory, shell, web, subagent, and package-install access are denied.
7. OpenCode may write only PROPOSED.patch.
8. The patch may target only dirty_python_lab.py.
9. git apply --check must pass before the disposable copy can change.
10. Protected tests are hashed before and after patch application.
11. Compile and the full unittest suite run against only the disposable project.
12. Failed tests can trigger another targeted-slice repair round.
13. The original source manifest is checked again at the end.
14. There is no original-source Apply button or API route.

Button meaning
--------------
REVIEW SYMBOL MAP
  Read-only review of the original target and proposed initial symbol selection.

SNAPSHOT DISPOSABLE COPY
  Copies the project to a new workspace and commits a Git baseline.

RUN SURGICAL BUILD + TEST
  Performs snapshot, slicing, restricted OpenCode patch generation, patch validation,
  disposable-only application, compile, tests, and targeted repair rounds.

APPLY LATEST PATCH TO DISPOSABLE
  Applies only the latest validated patch to the current disposable copy.

ROLLBACK DISPOSABLE
  Resets the disposable project to the baseline commit.

Model and endpoint
------------------
Model:
  Z:\FOXAI\Models\Chat\Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf

Endpoint:
  http://127.0.0.1:8080/v1

Configured context:
  16384

Not included / not changed
--------------------------
- No Engineering Workshop flow
- No tkinter
- No installer
- No shared Python runtime edit
- No live FOXAI edit
- No Preview 7 execution
- No automatic apply to the original Dirty Python Lab
