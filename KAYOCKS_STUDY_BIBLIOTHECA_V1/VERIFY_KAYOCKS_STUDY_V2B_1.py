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
import zipfile

EXPECTED_RESEARCH_DESK_SHA256 = "dd2d4fbb68e79e3011f767e0ea2bbc16dd56f23eb5bb14b1a81c86539c160519"
EXPECTED_V1_6_VERIFIER_SHA256 = "f5d1070f2e69c131c986d8b6b7bacd1e8d88223d53058775c58c928fb43b842a"
EXPECTED_V1_2_VERIFIER_SHA256 = "3c74030d778c5907986cd8b9da796edacadd1c44b3d2b3bceb1931147f450787"
EXPECTED_V1_2_1_VERIFIER_SHA256 = "c32925b6c86139c057e090fa17d6dcae6a4b70de4e56d00a54248b1fe93fc795"
EXPECTED_V1_2_2_VERIFIER_SHA256 = "d41640e33040a8aca045b8d70f4e3a7e9f2b4f7c6837adecce44b5f2cf27ff4f"
EXPECTED_V2A_1_VERIFIER_SHA256 = "9ca30e519f8221b44412efdbf8b245fe0bbd2fbe88bbba2a90b78103011c344d"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("kayocks_study_v2b_1_live", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_epub(
    path: Path,
    *,
    title: str,
    creator: str,
    with_cover: bool,
    encrypted: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_cover = (
        '<item id="cover" href="images/cover.png" media-type="image/png" properties="cover-image"/>'
        if with_cover else ""
    )
    package = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:test:{title}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator>{creator}</dc:creator>
    <dc:language>en</dc:language>
    <dc:publisher>FOXAI Fixture Press</dc:publisher>
    <dc:date>2026-07-20</dc:date>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    {manifest_cover}
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
        if encrypted:
            archive.writestr("META-INF/encryption.xml", "<encryption/>")
        archive.writestr("OEBPS/content.opf", package)
        archive.writestr("OEBPS/nav.xhtml", "<html><body><nav>Chapter One</nav></body></html>")
        archive.writestr("OEBPS/chapter1.xhtml", "<html><body><h1>Chapter One</h1></body></html>")
        if with_cover:
            archive.writestr("OEBPS/images/cover.png", b"\x89PNG\r\n\x1a\nFOXAI-COVER")


def request_json(base: str, path: str) -> tuple[int, dict]:
    with urlopen(base + path, timeout=5) as response:
        return int(response.status), json.loads(response.read().decode("utf-8"))


def request_bytes(base: str, path: str) -> tuple[int, str, bytes]:
    with urlopen(base + path, timeout=5) as response:
        return int(response.status), str(response.headers.get("Content-Type") or ""), response.read()


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

    web_source = (root / "core" / "foxai_web.py").read_text(encoding="utf-8")
    check("main_foxai_lifecycle_present", "BIBLIOTHECA_URL='http://127.0.0.1:8777'" in web_source and "KAYOCKS_STUDY_BIBLIOTHECA_V1" in web_source)
    check("controlled_research_desk_preserved", sha256(app / "research_desk.py") == EXPECTED_RESEARCH_DESK_SHA256)
    check("v1_6_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V1_6.py") == EXPECTED_V1_6_VERIFIER_SHA256)
    check("v1_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2.py") == EXPECTED_V1_2_VERIFIER_SHA256)
    check("v1_2_1_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2_1.py") == EXPECTED_V1_2_1_VERIFIER_SHA256)
    check("v1_2_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2_2.py") == EXPECTED_V1_2_2_VERIFIER_SHA256)
    check("v2a_1_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V2A_1.py") == EXPECTED_V2A_1_VERIFIER_SHA256)

    required_backend = (
        "def connect_epub_db(", "def inspect_epub(", "def scan_ebook_catalog(",
        "def list_ebooks(", "def epub_cover_record(", 'parsed.path == "/api/ebooks"',
        'parsed.path == "/epub/cover"', 'epub_database=data / "epub_catalog.sqlite3"',
        'epub_cache=data / "EPUB_Covers"',
    )
    check("epub_catalog_backend_present", all(token in source for token in required_backend))
    check("separate_sidecar_database", "CREATE TABLE IF NOT EXISTS ebooks" in source and "epub_catalog.sqlite3" in source)
    check("supported_formats_are_bounded", '{".epub", ".mobi", ".azw", ".azw3"}' in source)
    check("no_external_star_trek_scan", "E:\\Star Trek" not in source and "external_library_root" not in source)
    check("no_reader_or_read_aloud_yet", all(token not in source for token in (
        "/epub/read", "/api/epub/search", "speechSynthesis", "read_aloud", "audiobook",
    )))

    required_ui = (
        "Scan for New Books", "api('/api/ebooks')", "libraryEbooks", "ebookStatusLabel",
        "openLibraryItemDetail", "Embedded covers are copied only to a disposable local cache",
        "Advanced Library Tools", "Tile View", "List View", "Recently Added",
        "Search This Document", "Ask Agent Fox", "Use This Recipe", "Controlled Research Desk",
    )
    check("v2b_1_ui_present", all(token in html for token in required_ui))
    check("v2a_1_tiled_home_preserved", all(token in html for token in (
        'id="libraryHome"', 'id="advancedWorkspace" hidden', ".tiletrack{display:grid;grid-auto-flow:column",
        "function deterministicCoverStyle(", "function renderLibraryHome(",
    )))
    check("home_scan_button_present", html.count("Scan for New Books") >= 2)
    check("real_and_placeholder_covers_supported", "item.cover_url" in html and "deterministicCoverStyle(item)" in html)
    check("epub_detail_is_catalog_only", "Chapter reading, search, citations, progress, and read-aloud arrive in V2B.2." in html)

    tree = ast.parse(source)
    extracted = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "HTML" for target in node.targets):
            extracted = ast.literal_eval(node.value)
            break
    check("html_constant_extractable", extracted == html)
    check("single_script_block", html.count("<script>") == 1 and html.count("</script>") == 1)

    temp = Path(tempfile.mkdtemp(prefix="kayocks_study_v2b_1_http_"))
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
        )
        paths.library.mkdir(parents=True)
        paths.data.mkdir(parents=True)

        # A real PDF keeps the existing Bibliotheca path exercised.
        from pypdf import PdfWriter
        pdf_path = paths.library / "Manuals" / "Fixture Manual.pdf"
        pdf_path.parent.mkdir(parents=True)
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with pdf_path.open("wb") as handle:
            writer.write(handle)

        with_cover = paths.library / "Fiction" / "Star Trek" / "V2B Test Set" / "Doomsday Continuation.epub"
        no_cover = paths.library / "Fiction" / "Star Trek" / "V2B Test Set" / "X-Men Crossover.epub"
        encrypted = paths.library / "Fiction" / "Star Trek" / "V2B Test Set" / "Protected Test.epub"
        malformed = paths.library / "Fiction" / "Star Trek" / "V2B Test Set" / "Malformed Test.epub"
        mobi = paths.library / "Fiction" / "Star Trek" / "V2B Test Set" / "Archive Copy.mobi"
        make_epub(with_cover, title="Doomsday Continuation", creator="Fixture Author", with_cover=True)
        make_epub(no_cover, title="X-Men Crossover", creator="Fixture Author Two", with_cover=False)
        make_epub(encrypted, title="Protected Test", creator="Fixture Author", with_cover=True, encrypted=True)
        malformed.write_bytes(b"not an epub zip")
        mobi.write_bytes(b"preserved mobi fixture")

        original_hashes = {path.name: sha256(path) for path in (with_cover, no_cover, encrypted, malformed, mobi)}
        first = module.index_library(paths)
        check("first_scan_completed", first.get("ok") is True, first)
        check("pdf_api_inventory_preserved", first.get("pdfs_found") == 1 and first.get("database_documents") == 1, first)
        check("five_ebook_candidates_found", first.get("ebooks_found") == 5, first)
        check("two_readable_epubs", first.get("epubs_ready") == 2, first)
        check("three_review_items", first.get("ebooks_needing_review") == 3, first)
        check("cover_cache_created", paths.epub_cache.is_dir() and len(list(paths.epub_cache.iterdir())) == 1)
        check("original_ebooks_unchanged", original_hashes == {path.name: sha256(path) for path in (with_cover, no_cover, encrypted, malformed, mobi)})

        ebooks = module.list_ebooks(paths)
        by_title = {item["title"]: item for item in ebooks}
        check("epub_metadata_parsed", by_title["Doomsday Continuation"]["creator"] == "Fixture Author" and by_title["Doomsday Continuation"]["chapter_count"] == 1, ebooks)
        check("fiction_and_star_trek_classification", by_title["Doomsday Continuation"]["shelf"] == "Fiction" and by_title["Doomsday Continuation"]["collection"] == "Star Trek", ebooks)
        check("embedded_cover_available", bool(by_title["Doomsday Continuation"]["cover_url"]))
        check("placeholder_cover_fallback", not by_title["X-Men Crossover"]["cover_url"])
        check("encryption_marker_refused", by_title["Protected Test"]["status"] == "encrypted_or_protected" and by_title["Protected Test"]["encrypted"] == 1, ebooks)
        check("malformed_epub_reported", by_title["Malformed Test"]["status"] == "malformed", ebooks)
        check("mobi_reported_unsupported", by_title["Archive Copy"]["status"] == "unsupported_format", ebooks)

        main_conn = module.connect_db(paths)
        try:
            main_tables = {row[0] for row in main_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        finally:
            main_conn.close()
        check("bibliotheca_schema_not_extended_with_ebooks", "ebooks" not in main_tables, sorted(main_tables))
        check("sidecar_database_exists", module.epub_database_path(paths).is_file())

        second = module.index_library(paths)
        check("duplicate_rescan_is_incremental", second.get("ebooks_indexed_or_updated") == 0 and second.get("ebooks_unchanged") == 5, second)
        check("duplicate_rescan_keeps_single_cover", len(list(paths.epub_cache.iterdir())) == 1)

        server = module.StudyServer(("127.0.0.1", 0), module.StudyHandler, paths)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        status_code, status_payload = request_json(base, "/api/status")
        check("status_http_reports_epubs", status_code == 200 and status_payload.get("ebook_summary", {}).get("ready") == 2, status_payload)
        status_code, ebook_payload = request_json(base, "/api/ebooks")
        check("ebooks_http_200", status_code == 200 and len(ebook_payload.get("ebooks") or []) == 5, ebook_payload)
        star_trek = [item for item in ebook_payload["ebooks"] if item.get("collection") == "Star Trek" and item.get("status") == "ready"]
        check("star_trek_http_visibility", len(star_trek) == 2, star_trek)
        cover_id = by_title["Doomsday Continuation"]["id"]
        status_code, content_type, cover_body = request_bytes(base, f"/epub/cover?id={cover_id}")
        check("cover_http_200", status_code == 200 and content_type.startswith("image/png") and cover_body.startswith(b"\x89PNG"))
        status_code, documents_payload = request_json(base, "/api/documents?include_review=0")
        check("existing_pdf_documents_api_unchanged", status_code == 200 and len(documents_payload.get("documents") or []) == 1, documents_payload)
        status_code, search_payload = request_json(base, "/api/search?" + urlencode({"q": "nothing", "doc": "1"}))
        check("existing_pdf_search_api_returns_json", status_code == 200 and search_payload.get("ok") is True, search_payload)

        server.shutdown()
        server.server_close()
        server = None
        thread.join(timeout=3)
        thread = None

        no_cover.unlink()
        third = module.index_library(paths)
        check("removed_epub_catalog_cleanup", third.get("ebooks_removed_missing") == 1, third)
        check("removed_epub_absent", all(item["title"] != "X-Men Crossover" for item in module.list_ebooks(paths)))
        check("safe_member_rejects_traversal", _rejects_traversal(module))
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=3)
        shutil.rmtree(temp, ignore_errors=True)

    receipt = {
        "schema": "foxai.kayocks_study.v2b_1.verification.v1",
        "mission": "Kayock's Study V2B.1 — Native EPUB Discovery and Starfleet Archive Catalog",
        "result": "verified",
        "check_count": len(checks),
        "checks": checks,
        "safety": {
            "external_network_used": False,
            "loopback_http_only": True,
            "original_ebooks_modified": 0,
            "bibliotheca_schema_changed": False,
            "external_library_scanned": False,
        },
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


def _rejects_traversal(module) -> bool:
    try:
        module.safe_epub_member("OEBPS/content.opf", "../../outside.png")
    except ValueError:
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
