FOXAI ENGINEER EXACT FILE FIX — ONE CLICK

1. Close FOXAI.
2. Extract this folder directly into Z:\FOXAI.
3. Open Z:\FOXAI\ENGINEER_EXACT_FILE_ONE_CLICK.
4. Double-click INSTALL_ENGINEER_EXACT_FILE_FIX.bat.
5. Start FOXAI normally.

No PowerShell and no Engineering Workshop command.

After installation, this command:

/engineer explain what core\director.py does

opens that one file and explains it instead of searching the entire project.

Casbin remains installed because it successfully allowed the read-only Engineer
command. The problem was Engineer's path understanding, not authorization.

The installer changes only Z:\FOXAI\core\engineer_agent.py, creates a backup,
and automatically restores the original if the live test fails.
