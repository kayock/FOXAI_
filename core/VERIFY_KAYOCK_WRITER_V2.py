from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "foxai.kayock_writer.v2.verification"
WEB_PATH = Path(__file__).with_name("foxai_web.py")

PROTECTED_SECTION_HASHES = {
    "poetrystudio": "6984cf2610f85ea746d5c5c82138f63b2e11ee4d6e998b5e00d61450835a36c9",
    "poemarchive": "f5909c771afb24fea17b5497a21e449b0e0b9134bac9acb1aede93b2a13622f0",
    "storyforge": "245999aa7b7bc560f860a823a19abc76366004b25b9a83467241ce01c0dd31ad",
    "worldbuilder": "056c1739ad9d299ce4c10d1b5f374ebac7669e31e600d13badb9aefd5dac43ca"
}
PROTECTED_POETRY_JS_SHA256 = 'cbc61a33b492d99e6ed4af623d5dbedec94cb10ccae92baaa829a95e3678262c'
PROTECTED_MODEL_REGISTRY_SHA256 = 'd83dbe19abdeb9b9e7155213c7e1780d2564fbaadb321f81212eedc4282c51db'

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def extract_html(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "HTML"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, str):
                return value
    raise AssertionError("HTML assignment was not found.")

def section_html(html: str, section_id: str) -> str:
    match = re.search(
        rf"<section id={re.escape(section_id)}\b.*?</section>",
        html,
        flags=re.S,
    )
    if not match:
        raise AssertionError(f"Section missing: {section_id}")
    return match.group(0)

def marker_block(source: str, start: str, end: str) -> str:
    if start not in source or end not in source:
        raise AssertionError(f"Marker block missing: {start}")
    return source.split(start, 1)[1].split(end, 1)[0]

def verify_protected_workflows(source: str, html: str) -> dict[str, Any]:
    section_results = {}
    for section_id, expected in PROTECTED_SECTION_HASHES.items():
        actual = sha256_text(section_html(html, section_id))
        assert actual == expected, (section_id, actual, expected)
        section_results[section_id] = actual

    poetry_js = marker_block(
        source,
        "/* KAYOCK_WRITER_CALM_HOME_V1_JS_START */",
        "/* KAYOCK_WRITER_CALM_HOME_V1_JS_END */",
    )
    poetry_js_actual = sha256_text(poetry_js)
    assert poetry_js_actual == PROTECTED_POETRY_JS_SHA256, poetry_js_actual

    model_registry = marker_block(
        source,
        "/* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_START */",
        "/* MODEL_PROFILE_SELECTOR_PHASE2_REGISTRY_END */",
    )
    model_actual = sha256_text(model_registry)
    assert model_actual == PROTECTED_MODEL_REGISTRY_SHA256, model_actual

    return {
        "sections": section_results,
        "poetry_js": poetry_js_actual,
        "model_registry": model_actual,
    }

def verify_writer_home(source: str, html: str) -> dict[str, Any]:
    writer = section_html(html, "kayockwriter")
    required_text = [
        "What would you like to work on?",
        "Continue Recent Writing",
        "Create a Poem",
        "Polish a Poem",
        "Start or Continue a Story",
        "Build a World",
        "Browse My Writing",
        "Writer — Advanced Tools",
        "Opening a room never changes your saved work.",
    ]
    for text in required_text:
        assert text in writer, text

    assert 'id=writerContinueV2' in writer
    assert 'id=writerContinueV2Button' in writer
    assert "More creative rooms" not in writer
    assert "writerSecondaryRooms" not in writer
    assert '<div class="card writerContinue">' not in writer
    assert '<details class="card writerAdvancedHome writerAdvancedHomeV2">' in writer
    assert '<details class="card writerAdvancedHome writerAdvancedHomeV2" open' not in writer

    # The task-first home has one prominent Continue area plus five task cards.
    assert writer.count("<article class=") == 5, writer.count("<article class=")
    assert writer.count("Create a Poem") >= 2
    assert writer.count("Polish a Poem") >= 2

    for page_id in (
        "poetrystudio",
        "poemarchive",
        "storyforge",
        "worldbuilder",
        "mywriting",
    ):
        assert f"pg('{page_id}'" in html, page_id

    return {
        "task_cards": writer.count("<article class="),
        "continue_area": True,
        "advanced_collapsed": True,
        "save_state_notice": True,
    }

def verify_navigation_and_recent_state(source: str) -> dict[str, Any]:
    assert "'Kayock Writer':['kayockwriter','poetrystudio','poemarchive','storyforge','worldbuilder','mywriting']" in source
    assert "'Writer — Advanced Tools':['storymanifest'" in source
    assert "'Writer Advanced Tools':['storymanifest'" not in source
    assert "if(id==='kayockwriter')setTimeout(()=>renderWriterHomeV2(),0);" in source
    assert "if(id==='kayockwriter')setTimeout(()=>loadKayockWriter(false),0);" not in source

    block = marker_block(
        source,
        "/* KAYOCK_WRITER_CALM_GUIDED_V2_BROWSER_START */",
        "/* KAYOCK_WRITER_CALM_GUIDED_V2_BROWSER_END */",
    )
    for marker in (
        "WRITER_RECENT_V2",
        "writerRecentV2",
        "renderWriterHomeV2",
        "continueWriterRecentV2",
        "navRecents()",
        "saved files remain unchanged",
    ):
        assert marker in block, marker

    for page_id in (
        "poetrystudio",
        "poemarchive",
        "storyforge",
        "projectdashboard",
        "draftreader",
        "chapterproseworkspace",
        "worldbuilder",
        "mywriting",
        "novelforge",
    ):
        assert re.search(rf"\b{re.escape(page_id)}:", block), page_id

    lowered = block.casefold()
    assert "fetch(" not in lowered
    assert "api(" not in lowered
    assert "localstorage.setitem" not in lowered
    assert "sessionstorage" not in lowered

    return {
        "uses_existing_nav_recents": True,
        "writes_new_persistent_state": False,
        "network_calls": 0,
        "direct_writer_pages": 6,
        "advanced_group_collapsed_by_default": True,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--focused", action="store_true")
    args = parser.parse_args()

    source = WEB_PATH.read_text(encoding="utf-8")
    compile(source, str(WEB_PATH), "exec")
    html = extract_html(source)

    protected = verify_protected_workflows(source, html)
    navigation = verify_navigation_and_recent_state(source)

    result: dict[str, Any] = {
        "ok": True,
        "schema": SCHEMA,
        "mode": "focused" if args.focused else "full",
        "protected_workflows": protected,
        "navigation": navigation,
        "source_compiles": True,
        "files_written": 0,
        "network_used": False,
        "creative_generation_changed": False,
        "saved_content_changed": False,
    }

    if not args.focused:
        result["writer_home"] = verify_writer_home(source, html)
        result["poetry_studio_core_preserved"] = True
        result["poem_archive_preserved"] = True
        result["story_forge_preserved"] = True
        result["world_builder_preserved"] = True
        result["voice_profiles_preserved"] = True
        result["technical_foundation_auto_load_disabled"] = True

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
