from pathlib import Path
import json

from core_v10.department_registry import DepartmentRegistry

root = Path(__file__).resolve().parent
registry = DepartmentRegistry(root)
status = registry.status()

outbox = root / "OpsBridge" / "outbox"
outbox.mkdir(parents=True, exist_ok=True)
(outbox / "department_registry_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")

print("FOXAI Department Registry Status")
print("================================")
print()
print(f"OK: {status.get('ok')}")
print(f"Departments: {status.get('department_count')}")
print()
for dept in status.get("departments", []):
    print(f"- {dept.get('name')} [{dept.get('id')}]")
    print(f"  Officer: {dept.get('officer', {}).get('name')}")
    print(f"  Manifest: {'PASS' if dept.get('validation', {}).get('ok') else 'FAIL'}")
    print(f"  Health: {'PASS' if dept.get('health', {}).get('ok') else 'FAIL'}")
    print()
