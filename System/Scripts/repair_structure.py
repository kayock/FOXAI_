\
#!/usr/bin/env python3
"""Recreate missing KayocktheOS core folders."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
FOLDERS = [
    '00_START_HERE','Academy/Professors','Academy/Colleges','Academy/Lessons','Academy/Charter',
    'AI/Engines/Llamafile','AI/Engines/Ollama','AI/Engines/ComfyUI','AI/Models/Chat','AI/Models/Vision','AI/Models/Code','AI/Models/Embeddings','AI/Models/Image','AI/Model_Links',
    'Interface/Kayock_Browser','Interface/WebUI','Interface/Themes','Interface/Icons',
    'Knowledge/Linux','Knowledge/Windows','Knowledge/Networking','Knowledge/AI','Knowledge/Programming','Knowledge/Comics','Knowledge/Manuals','Knowledge/Personal_Notes',
    'RepairBay/Windows','RepairBay/Linux','RepairBay/Logs','RepairBay/Reports','RepairBay/Tools','RepairBay/ReadOnly_Scanners',
    'CreativeStudio/Images','CreativeStudio/Video','CreativeStudio/Audio','CreativeStudio/Comics','CreativeStudio/Prompts','CreativeStudio/Outputs',
    'Projects/Active','Projects/Archived','Projects/Experiments','System/Launchers','System/Config','System/Logs','System/Temp','System/Scripts','System/Backups',
    'The_Forge/Charters','The_Forge/Journal','The_Forge/Milestones'
]
for folder in FOLDERS:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)
print('KayocktheOS folder structure repaired.')
