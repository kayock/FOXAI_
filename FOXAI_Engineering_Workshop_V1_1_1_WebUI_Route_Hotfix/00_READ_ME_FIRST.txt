FOXAI ENGINEERING WORKSHOP V1.1.1 — WEBUI ROUTE HOTFIX

Why this is needed
------------------
Engineering Workshop V1.1 was installed correctly, but the live FOXAI WebUI
calls EngineerAgent.analyze(text) directly. That bypasses the V1.1 hook placed
inside EngineerAgent.handle(), so commands such as:

    /engineer workshop capabilities

were still treated as ordinary read-only Project search requests.

What this hotfix changes
------------------------
Only these live files are targeted:

    Z:\FOXAI\core\foxai_web.py
    Z:\FOXAI\core\engineer_agent.py

foxai_web.py routes explicit Workshop commands to the installed bridge before
falling back to the ordinary read-only Engineer analysis.

engineer_agent.py is adjusted only to preserve and display the exact bridge
import error if the bridge cannot load. This prevents another silent failure.

Safety
------
- Preview first
- One backup ZIP before changes
- No deletion
- No package installation
- No network activity
- Python compilation, bridge-import probe, and all Workshop tests
- Automatic restoration if validation fails

Install
-------
1. Double-click INSTALL_ENGINEERING_WORKSHOP_V1_1_1.bat for preview only.
2. Open Command Prompt in this folder and run:

       INSTALL_ENGINEERING_WORKSHOP_V1_1_1.bat --approve

3. Fully stop and restart the FOXAI WebUI server.
4. In Mission Console enter:

       /engineer workshop capabilities

Expected heading:

       ENGINEERING WORKSHOP CAPABILITIES
