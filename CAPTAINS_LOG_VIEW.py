from pathlib import Path
from core_v10.captains_log import CaptainsLog

root = Path(__file__).resolve().parent
log = CaptainsLog(root).build(limit=50)
print(CaptainsLog(root).render_text(log))
