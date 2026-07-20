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
import time
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import zipfile

EXPECTED_RESEARCH_DESK_SHA256 = "dd2d4fbb68e79e3011f767e0ea2bbc16dd56f23eb5bb14b1a81c86539c160519"
EXPECTED_V1_6_VERIFIER_SHA256 = "f5d1070f2e69c131c986d8b6b7bacd1e8d88223d53058775c58c928fb43b842a"
EXPECTED_V1_2_VERIFIER_SHA256 = "3c74030d778c5907986cd8b9da796edacadd1c44b3d2b3bceb1931147f450787"
EXPECTED_V1_2_2_VERIFIER_SHA256 = "d41640e33040a8aca045b8d70f4e3a7e9f2b4f7c6837adecce44b5f2cf27ff4f"
EXPECTED_V2A_1_VERIFIER_SHA256 = "9ca30e519f8221b44412efdbf8b245fe0bbd2fbe88bbba2a90b78103011c344d"
EXPECTED_V2B_1_VERIFIER_SHA256 = "b6fdf958dcd4b2cd2d45c3e3f79a84d61a7358757000261f35af929c527e8e38"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("kayocks_study_v2b_1_1_live", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_epub(path: Path, *, title: str, creator: str, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    package = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:test:{title}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator>{creator}</dc:creator>
    <dc:language>en</dc:language>
    <dc:publisher>Fixture Press</dc:publisher>
    <dc:date>2026-07-20</dc:date>
    <dc:description>{description}</dc:description>
    <dc:subject>Science Fiction</dc:subject>
    <dc:subject>Star Trek</dc:subject>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="chapter1"/></spine>
</package>'''
    container = '''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", package)
        archive.writestr("OEBPS/nav.xhtml", "<html><body><nav>Chapter One</nav></body></html>")
        archive.writestr("OEBPS/chapter1.xhtml", "<html><body><h1>Chapter One</h1></body></html>")


def request_json(base: str, path: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=8) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = {"message": body}
        return int(exc.code), parsed


def request_bytes(base: str, path: str) -> tuple[int, dict, bytes]:
    with urlopen(base + path, timeout=8) as response:
        headers = {key.casefold(): value for key, value in response.headers.items()}
        return int(response.status), headers, response.read()


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

    check("version_2b_1_1", module.APP_VERSION == "2B.1.1", module.APP_VERSION)
    check("controlled_research_desk_preserved", sha256(app / "research_desk.py") == EXPECTED_RESEARCH_DESK_SHA256)
    check("v1_6_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V1_6.py") == EXPECTED_V1_6_VERIFIER_SHA256)
    check("v1_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2.py") == EXPECTED_V1_2_VERIFIER_SHA256)
    check("v1_2_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2_2.py") == EXPECTED_V1_2_2_VERIFIER_SHA256)
    check("v2a_1_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V2A_1.py") == EXPECTED_V2A_1_VERIFIER_SHA256)
    check("v2b_1_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V2B_1.py") == EXPECTED_V2B_1_VERIFIER_SHA256)

    required_backend = (
        "def library_item_detail(", "def pdf_library_detail(", "def epub_library_detail(",
        "def connect_library_state_db(", "study_library_state.sqlite3",
        'parsed.path == "/api/library/item"', 'parsed.path == "/api/library/rating"',
        'parsed.path == "/epub/file"', "EPUB_CATALOG_PARSER_VERSION = 2",
    )
    check("universal_title_page_backend_present", all(token in source for token in required_backend))
    check("personal_rating_is_separate_sidecar", "CREATE TABLE IF NOT EXISTS library_item_state" in source and "study_library_state.sqlite3" in source)
    check("epub_summary_metadata_parser_present", all(token in source for token in ('first_xml_text(opf_root, "description")', 'all_xml_texts(opf_root, "subject")', '"description": description')))
    check("no_actual_reader_or_voice_engine_added", all(token not in source for token in ("speechSynthesis", "/epub/read", "/api/epub/search", "pyttsx3", "sapi.SpVoice")))

    required_ui = (
        'data-library-kind="${kind}"', 'data-library-id="${id}"',
        "document.addEventListener('click'", "Open title page for",
        'id="homeScanButton"', 'id="advancedScanButton"', 'id="homeScanStatus"', 'id="homeScanBar"',
        "paintHomeScanState", "setScanButtonsBusy", "scanStartPending",
        "Summary", "My Rating", "How to Open", "Read This to Me · Coming Soon",
        "Open or Save Original EPUB", "Open PDF", "Search This Document", "Ask Agent Fox",
    )
    check("title_page_and_scan_ui_present", all(token in html for token in required_ui))
    check("fragile_library_inline_handlers_removed", 'onclick="openLibraryItemDetail' not in html and "class=libraryrow onclick" not in html)
    check("native_buttons_preserve_keyboard_activation", 'type=button class="booktile libraryitem"' in html and 'type=button class="libraryrow libraryitem"' in html)
    check("scan_actions_use_one_verified_endpoint", html.count("api('/api/index',{method:'POST'})") == 1 and html.count('data-action="start-index"') >= 2)
    check("visible_scan_feedback_and_auto_refresh", "Starting the verified PDF and ebook scanner" in html and "refreshLibraryHome()" in html and "indexWasRunning&&!state.indexing" in html)
    check("epub_reader_limit_is_honest", "Chapter reading, search, citations, progress, and read-aloud arrive in V2B.2." in html)

    tree = ast.parse(source)
    extracted = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "HTML" for target in node.targets):
            extracted = ast.literal_eval(node.value)
            break
    check("html_constant_extractable", extracted == html)
    check("single_script_block", html.count("<script>") == 1 and html.count("</script>") == 1)

    temp = Path(tempfile.mkdtemp(prefix="kayocks_study_v2b_1_1_http_"))
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
            epub_database=temp / "Data" / "epub_catalog.sqlite3",
            epub_cache=temp / "Data" / "EPUB_Covers",
            library_state_database=temp / "Data" / "study_library_state.sqlite3",
        )
        paths.library.mkdir(parents=True)
        paths.data.mkdir(parents=True)

        from pypdf import PdfWriter
        pdf_path = paths.library / "Manuals" / "Fedora Fixture Guide.pdf"
        pdf_path.parent.mkdir(parents=True)
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.add_metadata({
            "/Title": "Fedora Fixture Guide",
            "/Author": "Fixture Author",
            "/Subject": "A concise fixture summary for the universal title page.",
            "/Creator": "FOXAI Verification",
        })
        with pdf_path.open("wb") as handle:
            writer.write(handle)

        epub_path = paths.library / "Fiction" / "Star Trek" / "V2B Test Set" / "Title Page Fixture.epub"
        make_epub(
            epub_path,
            title="Title Page Fixture",
            creator="Starfleet Archivist",
            description="A preserved Star Trek fixture used to verify summaries and ratings.",
        )
        originals = {"pdf": sha256(pdf_path), "epub": sha256(epub_path)}

        first = module.index_library(paths)
        check("fixture_scan_completed", first.get("ok") is True and first.get("pdfs_found") == 1 and first.get("epubs_ready") == 1, first)
        check("original_files_unchanged_after_scan", originals == {"pdf": sha256(pdf_path), "epub": sha256(epub_path)})

        pdf_detail = module.pdf_library_detail(paths, 1)
        epub_detail = module.epub_library_detail(paths, 1)
        check("pdf_metadata_title_page", pdf_detail.get("author") == "Fixture Author" and "concise fixture summary" in pdf_detail.get("summary", ""), pdf_detail)
        check("epub_metadata_title_page", epub_detail.get("creator") == "Starfleet Archivist" and "preserved Star Trek fixture" in epub_detail.get("summary", ""), epub_detail)
        check("epub_subjects_preserved", epub_detail.get("subjects") == ["Science Fiction", "Star Trek"], epub_detail)
        check("opening_guidance_present", "built-in PDF viewer" in pdf_detail.get("open_guidance", "") and "V2B.2" in epub_detail.get("open_guidance", ""))
        check("voice_control_reserved_not_active", "reserved" in pdf_detail.get("voice_status", "").casefold() and "approved local voice" in epub_detail.get("voice_status", "").casefold())

        main_conn = module.connect_db(paths)
        try:
            main_tables = {row[0] for row in main_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        finally:
            main_conn.close()
        epub_conn = module.connect_epub_db(paths)
        try:
            epub_tables = {row[0] for row in epub_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        finally:
            epub_conn.close()
        state_conn = module.connect_library_state_db(paths)
        try:
            state_tables = {row[0] for row in state_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        finally:
            state_conn.close()
        check("rating_table_not_in_bibliotheca_pdf_database", "library_item_state" not in main_tables, sorted(main_tables))
        check("rating_table_not_in_epub_catalog_database", "library_item_state" not in epub_tables, sorted(epub_tables))
        check("rating_table_only_in_state_sidecar", "library_item_state" in state_tables, sorted(state_tables))

        # Force an old parser marker; unchanged EPUB must be reparsed once.
        epub_conn = module.connect_epub_db(paths)
        try:
            row = epub_conn.execute("SELECT id,metadata_json FROM ebooks WHERE id=1").fetchone()
            metadata = json.loads(row["metadata_json"])
            metadata["parser_version"] = 1
            metadata["description"] = "stale description"
            epub_conn.execute("UPDATE ebooks SET metadata_json=? WHERE id=1", (json.dumps(metadata),))
            epub_conn.commit()
        finally:
            epub_conn.close()
        reparsed = module.index_library(paths)
        check("parser_revision_reindexes_unchanged_epub_once", reparsed.get("ebooks_indexed_or_updated") == 1, reparsed)
        check("reparse_restores_embedded_summary", "preserved Star Trek fixture" in module.epub_library_detail(paths, 1).get("summary", ""))
        incremental = module.index_library(paths)
        check("next_rescan_is_incremental", incremental.get("ebooks_indexed_or_updated") == 0 and incremental.get("ebooks_unchanged") == 1, incremental)

        server = module.StudyServer(("127.0.0.1", 0), module.StudyHandler, paths)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        status, payload = request_json(base, "/api/library/item?" + urlencode({"kind": "pdf", "id": 1}))
        check("pdf_title_page_http_200", status == 200 and payload.get("item", {}).get("author") == "Fixture Author", payload)
        status, payload = request_json(base, "/api/library/item?" + urlencode({"kind": "epub", "id": 1}))
        check("epub_title_page_http_200", status == 200 and payload.get("item", {}).get("original_epub_url") == "/epub/file?id=1", payload)

        status, payload = request_json(base, "/api/library/rating", method="POST", payload={"kind": "pdf", "id": 1, "rating": 4})
        check("pdf_rating_saved_http", status == 200 and payload.get("rating") == 4, payload)
        status, payload = request_json(base, "/api/library/rating", method="POST", payload={"kind": "epub", "id": 1, "rating": 5})
        check("epub_rating_saved_http", status == 200 and payload.get("rating") == 5, payload)
        status, payload = request_json(base, "/api/library/item?kind=epub&id=1")
        check("rating_persists_in_title_page", payload.get("item", {}).get("rating") == 5, payload)
        status, payload = request_json(base, "/api/library/rating", method="POST", payload={"kind": "epub", "id": 1, "rating": 9})
        check("invalid_rating_rejected", status == 400, payload)
        status, payload = request_json(base, "/api/library/rating", method="POST", payload={"kind": "epub", "id": 1, "rating": 0})
        check("rating_can_be_cleared", status == 200 and payload.get("rating") == 0, payload)

        status, headers, body = request_bytes(base, "/epub/file?id=1")
        check("original_epub_handoff_http_200", status == 200 and headers.get("content-type", "").startswith("application/epub+zip"), headers)
        check("original_epub_handoff_is_byte_exact", hashlib.sha256(body).hexdigest() == originals["epub"])
        check("epub_handoff_has_safe_disposition", "attachment" in headers.get("content-disposition", "").casefold(), headers)

        # Verify one scan endpoint, duplicate-start rejection, completion, and refreshed inventory.
        second_pdf = paths.library / "Manuals" / "New Scan Button Fixture.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with second_pdf.open("wb") as handle:
            writer.write(handle)
        original_index = module.index_library
        def slow_index(target_paths):
            time.sleep(0.35)
            return original_index(target_paths)
        module.index_library = slow_index
        status, payload = request_json(base, "/api/index", method="POST")
        check("home_scan_endpoint_starts", status == 202 and payload.get("ok") is True, payload)
        status2, payload2 = request_json(base, "/api/index", method="POST")
        check("duplicate_scan_start_rejected", status2 == 409 and payload2.get("ok") is False, payload2)
        deadline = time.time() + 10
        final_status = {}
        while time.time() < deadline:
            _, final_status = request_json(base, "/api/status")
            if not final_status.get("state", {}).get("indexing"):
                break
            time.sleep(0.08)
        module.index_library = original_index
        check("scan_completion_visible_in_status", final_status.get("state", {}).get("last_result", {}).get("database_documents") == 2, final_status)
        status, documents = request_json(base, "/api/documents?include_review=0")
        check("post_scan_inventory_contains_new_pdf", status == 200 and len(documents.get("documents") or []) == 2, documents)

        check("original_files_unchanged_after_title_actions", originals == {"pdf": sha256(pdf_path), "epub": sha256(epub_path)})
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=3)
        shutil.rmtree(temp, ignore_errors=True)

    receipt = {
        "schema": "foxai.kayocks_study.v2b_1_1.verification.v1",
        "mission": "Kayock's Study V2B.1.1 — Library Tile Actions, Universal Title Pages, and Home Scan Feedback",
        "result": "verified",
        "check_count": len(checks),
        "checks": checks,
        "safety": {
            "external_network_used": False,
            "loopback_http_only": True,
            "original_library_files_modified": 0,
            "bibliotheca_pdf_schema_changed": False,
            "epub_catalog_schema_changed": False,
            "rating_storage": "separate_local_sidecar",
            "active_epub_reader_added": False,
            "active_voice_engine_added": False,
        },
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
