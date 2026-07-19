FOXAI Engineering Workshop V1.2.1 — Casbin Preview Policy

Purpose
-------
Adds exactly one missing Casbin policy row:

p, operator, engineering_airlock, preview, allow

Why
---
Workshop capabilities does not require preview authorization, so it worked.
Workshop begin, locate, save-plan, and preview do require that action.
The installed Casbin policy had no matching allow row and therefore denied them.

Scope
-----
Targets only:
Config/engineering_airlock_policy.csv

Does not modify Python source, WebUI, model runtime, Study, Library, PDFs,
Writer, Repair Bay, ComfyUI, or model files.

Use
---
Preview:
INSTALL_ENGINEERING_WORKSHOP_V1_2_1_POLICY.bat

Apply:
INSTALL_ENGINEERING_WORKSHOP_V1_2_1_POLICY.bat --approve

The Python command may be used directly if needed:
Z:\FOXAI\Runtime\Desktop\python\python.exe INSTALL_ENGINEERING_WORKSHOP_V1_2_1_POLICY.py --approve

After installation, fully restart FOXAI WebUI because the Casbin enforcer is
cached inside the running Python process.
