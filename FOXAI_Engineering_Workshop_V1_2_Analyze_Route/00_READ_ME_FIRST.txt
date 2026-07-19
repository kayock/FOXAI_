FOXAI ENGINEERING WORKSHOP V1.2 — ANALYZE ROUTE

Purpose
-------
Connect explicit /engineer workshop commands at the route the current WebUI actually uses: EngineerAgent.analyze().

Safety boundary
---------------
This package targets ONE live file only:
  Z:\FOXAI\core\engineer_agent.py

It does NOT modify:
  core\foxai_web.py
  the chat/model server
  model files
  Kayock's Study
  Writer
  Repair Bay
  ComfyUI

It installs no packages, uses no network, deletes nothing, and does not start or stop the model.

Use
---
1. Run INSTALL_ENGINEERING_WORKSHOP_V1_2.bat for preview only.
2. Review that the only target is core\engineer_agent.py.
3. From Command Prompt in this folder, run:
     INSTALL_ENGINEERING_WORKSHOP_V1_2.bat --approve
4. The installer creates one backup, applies atomically, compiles the source, directly probes:
     /engineer workshop capabilities
   through EngineerAgent.analyze(), and reruns Workshop tests.
5. On any failure, engineer_agent.py is restored automatically.
6. Restart FOXAI WebUI and test:
     /engineer workshop capabilities

Manual rollback
---------------
Run ROLLBACK_ENGINEERING_WORKSHOP_V1_2.bat for preview, then:
  ROLLBACK_ENGINEERING_WORKSHOP_V1_2.bat --approve
