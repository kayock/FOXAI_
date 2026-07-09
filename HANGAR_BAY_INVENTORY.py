from pathlib import Path
from core_v10.hangar_bay_inspector import HangarBayInspector

root = Path(__file__).resolve().parent
inspector = HangarBayInspector(root)
result = inspector.write_inventory()
print(inspector.render_text(result["inventory"]))
print()
print("Inventory written to:")
print(result["path"])
