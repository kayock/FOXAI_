FOXAI WEBUI AGENT FOX EXACT FILE FIX — ONE CLICK

1. Close FOXAI WebUI.
2. Extract this folder directly into Z:\FOXAI.
3. Open Z:\FOXAI\AGENT_FOX_WEBUI_EXACT_FILE_ONE_CLICK.
4. Double-click INSTALL_AGENT_FOX_WEBUI_EXACT_FILE_FIX.bat.
5. Start FOXAI WebUI normally.

No PowerShell and no Engineering Workshop command.

After installation, normal WebUI chat can answer:

What does core\director.py do?

Agent Fox opens only that exact FOXAI file read-only and answers from its real
structure before model dispatch.

Both /api/chat/send and /api/chat/stream are covered.

Slash commands, Engineer, Workshop, Casbin, Red Canvas, Desktop integration,
and the existing self-knowledge adapter remain unchanged.

The installer changes only:

Z:\FOXAI\System\AgentFoxTechnicalCore\webui_self_knowledge_integration_v1.py

It creates a backup and automatically restores the original if the live test
fails.
