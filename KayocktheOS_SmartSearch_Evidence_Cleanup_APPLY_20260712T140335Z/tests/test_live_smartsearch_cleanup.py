from __future__ import annotations

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: test_live_smartsearch_cleanup.py FOXAI_ROOT")

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))

from core.smart_search import SmartSearch

search = SmartSearch(root)

data = search.layered_search("COMFY_MAIN")
all_items = [
    *data.get("primary", []),
    *data.get("history", []),
    *data.get("vendor", []),
]

for item in all_items:
    rel = str(item.get("file", "")).replace("\\", "/")
    top = rel.split("/", 1)[0].casefold()
    assert not rel.startswith(("Backup/", "Backups/")), rel
    assert not (
        top.startswith("kayocktheos_")
        and any(
            marker in top
            for marker in (
                "_apply_",
                "_preview_",
                "_patch_bundle_",
                "_checkpoint_",
            )
        )
    ), rel

assert any(
    str(item.get("file", "")).replace("\\", "/") == "core/foxai_web.py"
    for item in data.get("primary", [])
), data

memory_data = search.layered_search("input_box =")
assert all(
    not str(item.get("file", "")).replace("\\", "/").startswith("Memory/")
    for item in memory_data.get("primary", [])
), memory_data
assert any(
    str(item.get("file", "")).replace("\\", "/") == "ui/main_window.py"
    for item in memory_data.get("primary", [])
), memory_data

report = search.format_report("COMFY_MAIN")
assert (
    "Generated apply/preview/checkpoint bundles and backup trees are excluded."
    in report
), report

print("live_generated_artifact_exclusion=PASS")
print("live_source_priority=PASS")
print("live_memory_classification=PASS")
print("live_policy_disclosure=PASS")
