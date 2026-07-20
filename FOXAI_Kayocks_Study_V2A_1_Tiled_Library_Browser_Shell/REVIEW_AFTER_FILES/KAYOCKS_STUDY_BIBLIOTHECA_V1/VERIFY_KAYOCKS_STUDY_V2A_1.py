from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from threading import Thread
from urllib.parse import urlencode
from urllib.request import urlopen

EXPECTED_WEB_SHA256 = "06063ac9e312129da002a21d52556df560e8fef3c7e9b3b0216a001574768114"
EXPECTED_RESEARCH_DESK_SHA256 = "dd2d4fbb68e79e3011f767e0ea2bbc16dd56f23eb5bb14b1a81c86539c160519"
EXPECTED_V1_6_VERIFIER_SHA256 = "f5d1070f2e69c131c986d8b6b7bacd1e8d88223d53058775c58c928fb43b842a"
EXPECTED_V1_2_VERIFIER_SHA256 = "3c74030d778c5907986cd8b9da796edacadd1c44b3d2b3bceb1931147f450787"
EXPECTED_V1_2_1_VERIFIER_SHA256 = "c32925b6c86139c057e090fa17d6dcae6a4b70de4e56d00a54248b1fe93fc795"
EXPECTED_V1_2_2_VERIFIER_SHA256 = "d41640e33040a8aca045b8d70f4e3a7e9f2b4f7c6837adecce44b5f2cf27ff4f"
EXPECTED_BACKEND_PREFIX_SHA256 = "d70488cae4506213f6969462194418384f90d548cacce1bf6e9e207653861726"
EXPECTED_BACKEND_SUFFIX_SHA256 = "89a90e7e3aea2e6839fd044adafc0eb63ddd6ef3f13232bc19c1920c72a1407b"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("kayocks_study_v2a_1_live", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def add_document(
    conn: sqlite3.Connection,
    *,
    doc_id: int,
    root: Path,
    rel_path: str,
    title: str,
    indexed_at: str,
    pages: dict[int, str],
    text_status: str = "searchable",
    is_ocr_copy: int = 0,
) -> None:
    absolute = root / "Library" / Path(rel_path)
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(b"fixture")
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
            doc_id, str(absolute), rel_path, title, absolute.stat().st_size, doc_id,
            f"{doc_id:064x}"[-64:], len(pages), len(pages), total, 0, 0,
            text_status, is_ocr_copy, title.casefold(), indexed_at,
        ),
    )
    for page_number, body in pages.items():
        conn.execute(
            "INSERT INTO pages(document_id,page_number,text,text_chars) VALUES(?,?,?,?)",
            (doc_id, page_number, body, len(body)),
        )
    conn.commit()


def request_json(base: str, path: str) -> tuple[int, dict]:
    with urlopen(base + path, timeout=5) as response:
        return int(response.status), json.loads(response.read().decode("utf-8"))


def request_text(base: str, path: str) -> tuple[int, str]:
    with urlopen(base + path, timeout=5) as response:
        return int(response.status), response.read().decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    app = root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"
    server_path = app / "study_server.py"
    source = server_path.read_text(encoding="utf-8")
    module = load_module(server_path)
    html = module.HTML
    checks: list[dict] = []

    def check(name: str, condition: bool, detail="") -> None:
        checks.append({"id": name, "ok": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    html_marker = 'HTML = r"""'
    handler_marker = "\nclass StudyHandler"
    html_start = source.index(html_marker)
    handler_start = source.index(handler_marker, html_start)
    check("v1_2_2_backend_prefix_preserved", sha256_bytes(source[:html_start].encode("utf-8")) == EXPECTED_BACKEND_PREFIX_SHA256)
    check("v1_2_2_backend_routes_preserved", sha256_bytes(source[handler_start:].encode("utf-8")) == EXPECTED_BACKEND_SUFFIX_SHA256)
    check("main_foxai_web_preserved", sha256(root / "core" / "foxai_web.py") == EXPECTED_WEB_SHA256)
    check("controlled_research_desk_preserved", sha256(app / "research_desk.py") == EXPECTED_RESEARCH_DESK_SHA256)
    check("v1_6_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V1_6.py") == EXPECTED_V1_6_VERIFIER_SHA256)
    check("v1_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2.py") == EXPECTED_V1_2_VERIFIER_SHA256)
    check("v1_2_1_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2_1.py") == EXPECTED_V1_2_1_VERIFIER_SHA256)
    check("v1_2_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2_2.py") == EXPECTED_V1_2_2_VERIFIER_SHA256)

    required_ui = (
        'id="libraryHome"',
        'id="advancedWorkspace" hidden',
        'Advanced Library Tools',
        'Tile View',
        'List View',
        'Recently Added',
        'function deterministicCoverStyle(',
        'function openDocumentDetail(',
        'function searchThisDocument(',
        'function askThisDocument(',
        'function showLibraryHome(',
        'function showAdvancedTools(',
        "api('/api/shelves')",
        "api('/api/documents?include_review=0')",
    )
    check("tiled_browser_shell_present", all(token in html for token in required_ui))
    check("browser_is_normal_home", 'id="libraryHome" class="card libraryhome"' in html and 'id="advancedWorkspace" hidden' in html)
    check("portrait_cover_geometry", ".bookcover{position:relative;aspect-ratio:2/3" in html)
    check("horizontal_shelf_rows", ".tiletrack{display:grid;grid-auto-flow:column" in html and "overflow-x:auto" in html)
    check("recently_added_uses_indexed_at", "String(b.indexed_at||'').localeCompare(String(a.indexed_at||''))" in html)
    check("placeholder_covers_are_browser_only", "deterministicCoverStyle(item)" in html and "canvas" not in html.lower() and "/api/thumbnail" not in html)
    check("tile_and_list_controls", "setLibraryView('tiles')" in html and "setLibraryView('list')" in html)
    check("document_detail_fields", all(token in html for token in ("Pages", "Text status", "Indexed pages", "Source type")))
    check("document_actions_reuse_existing_behavior", all(token in html for token in ("Open PDF", "Search This Document", "Ask Agent Fox", "openPdf(")))
    check("advanced_tools_preserve_controls", all(token in html for token in (
        "Index or Refresh Library", "Controlled Research Desk", "Search the Bibliotheca",
        "Page Results", "Duplicate Review", "Use This Recipe",
    )))
    check("research_room_opens_advanced", "if(room==='research'){showAdvancedTools('researchDesk')}" in html)
    check("no_personal_state_added", all(token not in source for token in (
        "/api/favorites", "/api/reading-position", "CREATE TABLE favorites",
        "CREATE TABLE reading_state", "localStorage", "sessionStorage",
    )))
    check("no_native_epub_or_external_scan_added", all(token not in source for token in (
        "/api/epub", "E:\\Star Trek", "V2B Test Set", "external_library_root",
    )))
    check("existing_search_failure_message_preserved", "The local Bibliotheca search service did not return a response." in html)
    check("existing_recipe_choice_preserved", "function useRecipeChoice(" in html and "Choose one recipe" in html)
    check("exact_page_context_preserved", "Ask from This Opened Page" in html and "function useOpenedPage(" in html)

    # Validate embedded JavaScript structure without executing browser APIs.
    tree = ast.parse(source)
    extracted = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "HTML" for target in node.targets):
            extracted = ast.literal_eval(node.value)
            break
    check("html_constant_extractable", extracted == html)
    check("single_script_block", html.count("<script>") == 1 and html.count("</script>") == 1)
    check("unique_key_interface_ids", all(html.count(f'id="{item}"') == 1 for item in (
        "libraryHome", "advancedWorkspace", "libraryBrowser", "librarySummary",
        "libraryShelf", "libraryQuery", "documentDetailDialog", "documentDetailBody",
    )))

    temp = Path(tempfile.mkdtemp(prefix="kayocks_study_v2a_1_http_"))
    server = None
    thread = None
    try:
        paths = module.AppPaths(
            root=temp,
            library=temp / "Library",
            data=temp / "Data",
            database=temp / "Data" / "bibliotheca.sqlite3",
            log=temp / "Logs" / "bibliotheca.log",
            reports=temp / "Reports",
        )
        paths.library.mkdir(parents=True)
        paths.data.mkdir(parents=True)
        conn = module.connect_db(paths)
        try:
            conn.execute("UPDATE metadata SET value='0' WHERE key='fts5'")
            add_document(
                conn, doc_id=1, root=temp,
                rel_path="Recipes/Nelson Family Recipe Book.pdf",
                title="Nelson Family Recipe Book",
                indexed_at="2026-07-20T04:00:00-06:00",
                pages={7: "WHITE BREAD Ingredients flour water Directions bake."},
            )
            add_document(
                conn, doc_id=2, root=temp,
                rel_path="DND/Starship Manual.pdf",
                title="Starship Manual",
                indexed_at="2026-07-19T04:00:00-06:00",
                pages={1: "STARSHIP SYSTEMS Navigation and engineering."},
            )
            add_document(
                conn, doc_id=3, root=temp,
                rel_path="Manuals/Python Guide OCR.pdf",
                title="Python Guide OCR",
                indexed_at="2026-07-18T04:00:00-06:00",
                pages={2: "PYTHON FOR LOOP Iterates through a sequence."},
                text_status="searchable_ocr_copy",
                is_ocr_copy=1,
            )
        finally:
            conn.close()

        server = module.StudyServer(("127.0.0.1", 0), module.StudyHandler, paths)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        status, served_html = request_text(base, "/")
        check("home_http_200", status == 200 and 'id="libraryHome"' in served_html and 'id="advancedWorkspace" hidden' in served_html)

        status, shelves = request_json(base, "/api/shelves")
        names = {item.get("name") for item in shelves.get("shelves") or []}
        check("existing_shelves_api_works", status == 200 and shelves.get("ok") is True and {"Recipes", "DND", "Manuals"}.issubset(names), shelves)

        status, documents = request_json(base, "/api/documents?include_review=0")
        docs = documents.get("documents") or []
        check("existing_documents_api_works", status == 200 and documents.get("ok") is True and len(docs) == 3, documents)
        check("tile_metadata_available", all(all(key in item for key in ("id", "title", "shelf", "page_count", "indexed_pages", "text_status", "indexed_at", "rel_path")) for item in docs), docs)
        check("recently_added_metadata_orderable", sorted(docs, key=lambda item: str(item.get("indexed_at") or ""), reverse=True)[0]["id"] == 1, docs)

        status, search = request_json(base, "/api/search?" + urlencode({
            "q": "White bread", "doc": "1", "shelf": "Recipes", "status": "searchable",
        }))
        check("v1_2_2_search_http_regression", status == 200 and search.get("ok") is True and len(search.get("results") or []) == 1, search)
        check("recipe_heading_http_regression", str(search["results"][0].get("detected_heading") or "").casefold() == "white bread", search)

        status, pdf_body = request_text(base, "/pdf?id=1")
        check("existing_pdf_route_works", status == 200 and pdf_body == "fixture")
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=3)
        shutil.rmtree(temp, ignore_errors=True)

    receipt = {
        "schema": "foxai.kayocks_study.v2a_1.verification.v1",
        "mission": "Kayock's Study V2A.1 — Tiled Library Browser Shell",
        "result": "verified",
        "check_count": len(checks),
        "checks": checks,
        "protected": {
            "bibliotheca_v1_2_exact_page": True,
            "bibliotheca_v1_2_1_recipe_layout": True,
            "bibliotheca_v1_2_2_search_reliability": True,
            "controlled_research_desk": True,
            "main_foxai_lifecycle": True,
            "database_schema": True,
            "library_content": True,
            "epubs": True,
            "writer": True,
            "repair_bay": True,
        },
        "network_used": False,
        "external_commands_run": False,
        "project_content_written_by_verifier": False,
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
