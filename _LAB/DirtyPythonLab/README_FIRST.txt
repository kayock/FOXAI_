FOXAI DIRTY PYTHON LAB 0.2.0
============================

PURPOSE
-------
A standalone local browser app using Python's standard library only.
No tkinter. No GUI package install. No Workshop mission. No installer.

ONE-CLICK START
---------------
1. Put this entire DirtyPythonLab folder at:
   Z:\FOXAI\_LAB\DirtyPythonLab

2. Make sure the shared Qwen endpoint is running at:
   http://127.0.0.1:8080/v1/chat/completions

3. Double-click:
   START_DIRTY_PYTHON_LAB.bat

4. Type a plain-language request and press the large:
   RUN & AUTO-REPAIR button

WHAT IT DOES
------------
- Sends the plain-language request to Qwen.
- Extracts the generated Python script.
- Saves it in a new, separate run folder.
- Runs it with the Hanger Bay Python using isolated mode.
- Captures exact stdout and stderr.
- Sends failures back to Qwen for repair.
- Reruns up to two repaired replacements.
- Saves every attempt and RESULT.json without overwriting older runs.

NEW IN 0.2.0
------------
- Large System Readiness panel for Python, Qwen, and portable VS Code.
- Automatically searches the known portable VS Code folder for Code.exe.
- Remembers the exact verified Code.exe path in lab_state.json.
- Enables OPEN IN PORTABLE VS CODE only after Code.exe is verified.
- Shows recent saved runs in the browser.
- Opens any listed run folder with one button.
- If the lab is already running on port 8788, the launcher reopens it instead
  of starting a duplicate server.

WORKSPACE BUTTONS
-----------------
OPEN WORKSPACE opens:
Z:\FOXAI\_LAB\DirtyPythonLab

FIND PORTABLE VS CODE searches only under:
Z:\Hanger Bay\Development\VSCode\4fe60c8b1c

OPEN IN PORTABLE VS CODE launches the exact verified Code.exe and passes the
DirtyPythonLab workspace folder to it. No guessed executable path is launched.

The separate LOCATE_PORTABLE_VSCODE.bat performs the same read-only discovery
without starting the browser app.

ONE-CLICK LIVE ACCEPTANCE
-------------------------
RUN_LIVE_ACCEPTANCE_CHECK.bat uses the real Hanger Bay Python and real shared
Qwen endpoint to generate and run one harmless print script. It requires no
prompt typing and saves exact evidence in the normal runs folder.

ROLLBACK / REMOVAL
------------------
This build does not install services, registry entries, startup items, Python
packages, or GUI frameworks. To remove it, stop the lab and move or delete the
DirtyPythonLab folder. Individual generated runs are under the runs folder.

To return to 0.1.0, replace only the packaged application files with the older
0.1.0 package. Existing run folders remain separate and are not modified.

IMPORTANT SAFETY BOUNDARY
-------------------------
Generated Python is real executable code. The lab runs it from a disposable
run folder with no shell, a timeout, isolated Python mode, and no user-site
packages. This is not a full Windows sandbox. Read the requested task before
running anything that could intentionally change files outside the workspace.
