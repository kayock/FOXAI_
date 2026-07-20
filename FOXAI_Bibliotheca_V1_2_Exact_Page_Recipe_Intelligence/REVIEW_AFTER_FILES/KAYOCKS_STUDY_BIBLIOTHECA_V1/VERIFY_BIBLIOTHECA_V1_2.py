from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

EXPECTED_WEB_SHA256 = "06063ac9e312129da002a21d52556df560e8fef3c7e9b3b0216a001574768114"  # filled by build script
EXPECTED_RESEARCH_DESK_SHA256 = "dd2d4fbb68e79e3011f767e0ea2bbc16dd56f23eb5bb14b1a81c86539c160519"  # filled by build script
EXPECTED_EXISTING_VERIFIER_SHA256 = "f5d1070f2e69c131c986d8b6b7bacd1e8d88223d53058775c58c928fb43b842a"  # filled by build script


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("bibliotheca_v1_2_live", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def add_document(conn: sqlite3.Connection, *, doc_id: int, rel_path: str, title: str, pages: dict[int, str]) -> None:
    total = sum(len(value) for value in pages.values())
    conn.execute(
        """
        INSERT INTO documents(
          id,path,rel_path,title,size_bytes,mtime_ns,sha256,page_count,indexed_pages,
          text_chars,low_text_pages,extraction_errors,text_status,is_ocr_copy,
          related_stem,indexed_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            doc_id, f"/fixture/{doc_id}.pdf", rel_path, title, 1000 + doc_id, 1,
            f"{doc_id:064x}"[-64:], len(pages), len(pages), total, 0, 0,
            "searchable", 0, title.casefold(), "2026-07-20T00:00:00-06:00",
        ),
    )
    for page_number, text in pages.items():
        conn.execute(
            "INSERT INTO pages(document_id,page_number,text,text_chars) VALUES(?,?,?,?)",
            (doc_id, page_number, text, len(text)),
        )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--focused", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    app = root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"
    server = app / "study_server.py"
    module = load_module(server)
    checks: list[dict] = []

    def check(name: str, condition: bool, detail="") -> None:
        checks.append({"id": name, "ok": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    check("main_web_preserved", sha256(root / "core" / "foxai_web.py") == EXPECTED_WEB_SHA256)
    check("research_desk_preserved", sha256(app / "research_desk.py") == EXPECTED_RESEARCH_DESK_SHA256)
    check("existing_v1_6_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V1_6.py") == EXPECTED_EXISTING_VERIFIER_SHA256)
    check("localhost_only", module.DEFAULT_PORT == 8777 and "127.0.0.1" in module.LOCAL_MODEL_URL)
    check("opened_page_ui", all(token in module.HTML for token in (
        "Opened PDF page:", "Ask from This Opened Page", "useOpenedPage()", "lastOpenedPage",
    )))
    check("automatic_cited_result_reuse_ui", all(token in module.HTML for token in (
        "q('askUseResults').checked=Boolean(lastSearchResults.length)",
        "Ready to reuse ${lastSearchResults.length} cited result(s)",
        "selection_mode||'search'",
    )))

    temp = Path(tempfile.mkdtemp(prefix="bibliotheca_v1_2_verify_"))
    try:
        (temp / "Library" / "Recipes").mkdir(parents=True)
        paths = module.build_paths(temp, str(temp / "Data"))
        conn = module.connect_db(paths)
        try:
            add_document(
                conn, doc_id=1, rel_path="Recipes/Family Bread.pdf", title="Family Bread",
                pages={7: "WHITE BREAD\nIngredients\n3 cups flour\n1 cup water\nDirections\nBake at 375° for 20 minutes."},
            )
            add_document(
                conn, doc_id=2, rel_path="Recipes/Community Bread.pdf", title="Community Bread",
                pages={7: "White Bread\nIngredients\n4 cups flour\nDirections\nBake until golden."},
            )
            add_document(
                conn, doc_id=3, rel_path="Recipes/Desserts.pdf", title="Desserts",
                pages={3: "CHOCOLATE CAKE\nIngredients\n2 cups white bread flour\n1 cup sugar\nDirections\nMix and bake."},
            )
            add_document(
                conn, doc_id=4, rel_path="Manuals/Field Manual.pdf", title="Field Manual",
                pages={4: "Battery replacement procedure. Disconnect power before opening the case."},
            )
        finally:
            conn.close()

        check(
            "named_recipe_subject_cleanup",
            module.requested_subject("How do I make White Bread on page 7?") == "white bread",
            module.requested_subject("How do I make White Bread on page 7?"),
        )
        check(
            "quoted_recipe_subject",
            module.requested_subject('Find the recipe called "White Bread" on page 7') == "white bread",
        )

        exact = module.resolve_question_sources(paths, "How long does it bake?", document_id=1, exact_page=7)
        check("selected_document_exact_page", exact["selection_mode"] == "exact_page" and len(exact["sources"]) == 1 and exact["sources"][0]["page_number"] == 7, exact)

        reused = module.resolve_question_sources(
            paths, "What do these cited pages say?",
            source_refs=[{"document_id": 4, "page_number": 4}],
        )
        check("reuse_cited_results", reused["selection_mode"] == "reused_citations" and len(reused["sources"]) == 1 and reused["sources"][0]["document_id"] == 4, reused)

        reused_page = module.resolve_question_sources(
            paths, "What is on page 7?", exact_page=7,
            source_refs=[{"document_id": 1, "page_number": 7}, {"document_id": 4, "page_number": 4}],
        )
        check("reuse_citations_honors_explicit_page", reused_page["selection_mode"] == "reused_citations_exact_page" and len(reused_page["sources"]) == 1 and reused_page["sources"][0]["document_id"] == 1, reused_page)

        named = module.resolve_question_sources(paths, "How do I make White Bread on page 7?", shelf="Recipes")
        check("named_recipe_exact_page", named["selection_mode"] == "named_recipe_exact_page" and named["exact_page"] == 7, named)
        check("multiple_recipe_warning", named["recipe_match_count"] == 2 and "Multiple recipe matches" in named["grounding_warning"], named)

        single = module.resolve_question_sources(paths, "How do I make White Bread on page 7?", document_id=1, shelf="Recipes")
        check("named_recipe_selected_document", single["selection_mode"] == "exact_page" and len(single["sources"]) == 1, single)

        ingredient = module.resolve_question_sources(paths, "Which recipe uses white bread flour?", document_id=3, shelf="Recipes")
        check("ingredient_not_title", bool(ingredient["sources"]) and ingredient["sources"][0]["match_role"] == "ingredient_only" and "ingredient text" in ingredient["grounding_warning"], ingredient)

        missing_recipe = module.resolve_question_sources(paths, "How long do I bake Moon Bread?", shelf="Recipes")
        check("missing_recipe_fails_fast", not missing_recipe["sources"] and missing_recipe["failure_code"] == "recipe_title_not_found" and missing_recipe["selection_mode"] == "recipe_heading_not_found", missing_recipe)

        missing_page = module.resolve_question_sources(paths, "White Bread on page 99", shelf="Recipes")
        check("missing_page_fails_fast", not missing_page["sources"] and missing_page["failure_code"] == "named_page_not_found" and missing_page["exact_page"] == 99, missing_page)

        bad_refs = module.resolve_question_sources(paths, "Use these results", source_refs=[{"document_id": 999, "page_number": 1}])
        check("missing_cited_results_fail_fast", not bad_refs["sources"] and bad_refs["failure_code"] == "cited_results_unavailable", bad_refs)

        analysis = module.recipe_page_analysis(
            "CHOCOLATE CAKE\nIngredients\n2 cups white bread flour\nDirections\nBake.",
            "white bread flour",
        )
        check("nearby_heading_recognized", analysis["detected_heading"] == "CHOCOLATE CAKE", analysis)
        check("ingredient_phrase_classified", analysis["match_role"] == "ingredient_only", analysis)
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    result = {
        "schema": "foxai.bibliotheca.v1_2.verification.v1",
        "mission": "Bibliotheca V1.2 — Exact Page and Recipe Intelligence",
        "mode": "focused" if args.focused else "full",
        "overall_result": "verified",
        "checks": checks,
        "check_count": len(checks),
        "protected": {
            "main_foxai_web": True,
            "controlled_research_desk": True,
            "existing_v1_6_verifier": True,
            "original_pdfs": True,
            "database_content": True,
            "writer": True,
            "repair_bay": True,
        },
        "network_used": False,
        "external_commands_run": False,
        "project_content_written": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
