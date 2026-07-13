from __future__ import annotations

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: test_live_smartsearch_root_staging_cleanup.py FOXAI_ROOT"
    )

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))

from core.smart_search import SmartSearch

search = SmartSearch(root)

def all_items(data):
    return [
        *data.get("primary", []),
        *data.get("history", []),
        *data.get("vendor", []),
    ]

comfy = search.layered_search("COMFY_MAIN")
comfy_items = all_items(comfy)

forbidden_root_dirs = {
    "backup",
    "backups",
    "baseline",
    "candidate",
    "payload",
}

for item in comfy_items:
    rel = str(item.get("file", "")).replace("\\", "/")
    top = rel.split("/", 1)[0].casefold()

    assert top not in forbidden_root_dirs, rel
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
    for item in comfy.get("primary", [])
), comfy

input_search = search.layered_search("input_box =")
assert any(
    str(item.get("file", "")).replace("\\", "/") == "ui/main_window.py"
    for item in input_search.get("primary", [])
), input_search
assert all(
    not str(item.get("file", "")).replace("\\", "/").startswith("Memory/")
    for item in input_search.get("primary", [])
), input_search

report = search.format_report("COMFY_MAIN")
assert (
    "Generated apply/preview/checkpoint bundles and backup trees are excluded."
    in report
), report

print("live_root_candidate_exclusion=PASS")
print("live_root_payload_exclusion=PASS")
print("live_root_baseline_exclusion=PASS")
print("live_named_bundle_exclusion=PASS")
print("live_source_priority=PASS")
print("live_memory_classification=PASS")
print("live_policy_disclosure=PASS")
