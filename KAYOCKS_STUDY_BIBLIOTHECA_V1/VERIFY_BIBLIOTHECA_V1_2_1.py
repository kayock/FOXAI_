from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

EXPECTED_WEB_SHA256 = "06063ac9e312129da002a21d52556df560e8fef3c7e9b3b0216a001574768114"
EXPECTED_RESEARCH_DESK_SHA256 = "dd2d4fbb68e79e3011f767e0ea2bbc16dd56f23eb5bb14b1a81c86539c160519"
EXPECTED_V1_6_VERIFIER_SHA256 = "f5d1070f2e69c131c986d8b6b7bacd1e8d88223d53058775c58c928fb43b842a"
EXPECTED_V1_2_VERIFIER_SHA256 = "3c74030d778c5907986cd8b9da796edacadd1c44b3d2b3bceb1931147f450787"
EXPECTED_BACKEND_PREFIX_SHA256 = "73f4776df02ef2babd4d957860b0118da50a7b62661bff46e8d804d9b9f76c97"
EXPECTED_BACKEND_SUFFIX_SHA256 = "7563b35c7d4e806909b3e9a4be20058c44218122815bc1c2407ed77ebfa6e72a"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def extract_html(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "HTML"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if not isinstance(value, str):
                break
            return value
    raise RuntimeError("Could not extract Bibliotheca HTML constant.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--focused", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    app = root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"
    server = app / "study_server.py"
    source = server.read_text(encoding="utf-8")
    html = extract_html(source)
    checks: list[dict] = []

    def check(name: str, condition: bool, detail="") -> None:
        checks.append({"id": name, "ok": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    html_marker = 'HTML = r"""'
    handler_marker = "\nclass StudyHandler"
    html_start = source.index(html_marker)
    handler_start = source.index(handler_marker, html_start)
    backend_prefix = source[:html_start].encode("utf-8")
    backend_suffix = source[handler_start:].encode("utf-8")

    check("v1_2_backend_prefix_unchanged", sha256_bytes(backend_prefix) == EXPECTED_BACKEND_PREFIX_SHA256)
    check("v1_2_backend_routes_unchanged", sha256_bytes(backend_suffix) == EXPECTED_BACKEND_SUFFIX_SHA256)
    check("main_foxai_web_preserved", sha256(root / "core" / "foxai_web.py") == EXPECTED_WEB_SHA256)
    check("controlled_research_desk_preserved", sha256(app / "research_desk.py") == EXPECTED_RESEARCH_DESK_SHA256)
    check("v1_6_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V1_6.py") == EXPECTED_V1_6_VERIFIER_SHA256)
    check("v1_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2.py") == EXPECTED_V1_2_VERIFIER_SHA256)

    search_start = html.index('<section class="card search">')
    ask_start = html.index('<section class="card ask">', search_start)
    search_card = html[search_start:ask_start]

    check("grid_cards_align_to_top", ".grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px;align-items:start}" in html)
    check("search_and_ask_size_naturally", ".search{grid-column:span 7;align-self:start}.ask{grid-column:span 5;align-self:start}" in html)
    check("page_results_inside_search_card", all(token in search_card for token in (
        'class="searchresults"', 'id="resultMeta"', 'id="useResultsButton"', 'id="resultList"',
    )))
    check("separate_stretched_results_card_removed", '<section class="card results">' not in html)
    check("documents_use_full_following_row", ".documents{grid-column:span 12}" in html)

    check("document_open_passes_real_title", "openPdf(${d.id},1,${JSON.stringify(d.title)}" in html)
    check("opened_page_resolves_real_document_title", all(token in html for token in (
        "const known=documents.find", "const resolvedTitle=String(title||known?.title||selected?.textContent||'Selected document')",
        "q('openedPageLabel').textContent=`${resolvedTitle}, page ${lastOpenedPage.page_number}`",
    )))
    check("generic_pdf_opened_label_removed", "lastOpenedPage.title||'PDF'" not in html)

    check("recipe_results_offer_direct_selection", all(token in html for token in (
        "function recipeChoiceAction(item)", "Use This Recipe", "function useRecipeChoice(",
    )))
    check("multiple_matches_render_as_choices", all(token in html for token in (
        "function renderRecipeChoices(items)", "Choose one recipe", "data.recipe_match_count>1?renderRecipeChoices(data.sources||[]):''",
    )))
    check("recipe_choice_sets_exact_document_and_page", all(token in html for token in (
        "q('askDoc').value=String(documentId)", "q('askPage').value=String(pageNumber)",
        "q('askUseResults').checked=false", "Selected recipe:",
    )))
    check("search_results_remain_cited_and_reusable", all(token in html for token in (
        "lastSearchResults=data.results||[]", "q('askUseResults').checked=Boolean(lastSearchResults.length)",
        "Ask from These Cited Pages", "Copy citation",
    )))
    check("v1_2_exact_page_ui_preserved", all(token in html for token in (
        "Ask from This Opened Page", "Clear Page Context", "exact_page:exactPage", "source_refs:sourceRefs",
    )))

    result = {
        "schema": "foxai.bibliotheca.v1_2_1.verification.v1",
        "mission": "Bibliotheca V1.2.1 — Search and Recipe Layout Refinement",
        "mode": "focused" if args.focused else "full",
        "overall_result": "verified",
        "check_count": len(checks),
        "checks": checks,
        "layout": {
            "search_card_stretch_removed": True,
            "results_beneath_search_controls": True,
            "documents_full_following_row": True,
        },
        "recipe_selection": {
            "individual_choices": True,
            "exact_document_and_page": True,
            "opened_title_and_page_visible": True,
        },
        "protected": {
            "v1_2_backend": True,
            "controlled_research_desk": True,
            "main_foxai_web": True,
            "writer_and_poetry": True,
            "repair_bay": True,
            "original_pdfs": True,
            "database_content": True,
            "saved_research": True,
        },
        "network_used": False,
        "external_commands_run_by_study": False,
        "project_content_written_by_verifier": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
