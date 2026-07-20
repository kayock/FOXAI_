from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import zipfile

EXPECTED_RESEARCH_DESK_SHA256 = "dd2d4fbb68e79e3011f767e0ea2bbc16dd56f23eb5bb14b1a81c86539c160519"
EXPECTED_V1_2_VERIFIER_SHA256 = "3c74030d778c5907986cd8b9da796edacadd1c44b3d2b3bceb1931147f450787"
EXPECTED_V1_2_2_VERIFIER_SHA256 = "d41640e33040a8aca045b8d70f4e3a7e9f2b4f7c6837adecce44b5f2cf27ff4f"
EXPECTED_V2A_1_VERIFIER_SHA256 = "9ca30e519f8221b44412efdbf8b245fe0bbd2fbe88bbba2a90b78103011c344d"
EXPECTED_V2B_1_VERIFIER_SHA256 = "b6fdf958dcd4b2cd2d45c3e3f79a84d61a7358757000261f35af929c527e8e38"
EXPECTED_V2B_1_1_VERIFIER_SHA256 = "483439194f67c790a62678388abdcb8d564c725dd73060731596709d6599aa55"

PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("kayocks_study_v2b_2_live", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_reader_epub(path: Path, *, title: str = "Reader Fixture", fixed_layout: bool = False, malformed_chapter: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    layout = '<meta property="rendition:layout">pre-paginated</meta>' if fixed_layout else ''
    package = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:test:{title}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator>Starfleet Archivist</dc:creator>
    <dc:language>en</dc:language>
    <dc:publisher>Fixture Press</dc:publisher>
    <dc:date>2026-07-20</dc:date>
    <dc:description>A multi-chapter fixture for the native Study reader.</dc:description>
    {layout}
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="Text/chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter2" href="Text/chapter2.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="Styles/book.css" media-type="text/css"/>
    <item id="image" href="Images/pixel.png" media-type="image/png"/>
    <item id="font" href="Fonts/fixture.woff" media-type="font/woff"/>
  </manifest>
  <spine><itemref idref="chapter1"/><itemref idref="chapter2"/></spine>
</package>'''
    container = '''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''
    nav = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body>
<nav epub:type="toc"><ol>
<li><a href="Text/chapter1.xhtml#start">Part One</a><ol><li><a href="Text/chapter2.xhtml#destination">Nested Chapter Two</a></li></ol></li>
</ol></nav></body></html>'''
    chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head>
<title>Chapter One</title><link rel="stylesheet" href="../Styles/book.css"/>
<style>@import url(https://evil.example/bad.css); .inline{color:#663399;background-image:url(https://evil.example/tracker.png)}</style>
<script>alert('blocked')</script></head>
<body onload="steal()"><h1 id="start" onclick="bad()">Chapter One</h1>
<p class="inline">Safe text <a href="chapter2.xhtml#destination">next chapter</a>.</p>
<img src="../Images/pixel.png" onerror="bad()" alt="fixture image"/>
<img src="https://evil.example/remote.png" alt="remote image"/>
<form action="https://evil.example"><input name="secret"/><button>Send</button></form>
</body></html>'''
    if malformed_chapter:
        chapter1 = "<html><body><h1 id='start'>Malformed but readable<script>bad()</script><p>Still here"
    chapter2 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Chapter Two</title><link rel="stylesheet" href="../Styles/book.css"/></head>
<body><h1 id="destination">Chapter Two</h1><p>Second chapter content.</p><a href="#destination">local fragment</a></body></html>'''
    css = '''@import url("https://evil.example/import.css");
@font-face{font-family:Fixture;src:url('../Fonts/fixture.woff') format('woff')}
body{font-family:Fixture,serif;background-image:url('../Images/pixel.png')}
p{line-height:1.6}.bad{width:expression(alert(1));background:url(https://evil.example/remote.png)}'''
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", package)
        archive.writestr("OEBPS/nav.xhtml", nav)
        archive.writestr("OEBPS/Text/chapter1.xhtml", chapter1)
        archive.writestr("OEBPS/Text/chapter2.xhtml", chapter2)
        archive.writestr("OEBPS/Styles/book.css", css)
        archive.writestr("OEBPS/Images/pixel.png", PIXEL_PNG)
        archive.writestr("OEBPS/Fonts/fixture.woff", b"fixture-font-bytes")


def make_encrypted_epub(path: Path) -> None:
    make_reader_epub(path, title="Protected Fixture")
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("META-INF/encryption.xml", "<encryption/>")


def request_json(base: str, path: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = {"message": body}
        return int(exc.code), parsed


def request_bytes(base: str, path: str) -> tuple[int, dict, bytes]:
    try:
        with urlopen(base + path, timeout=10) as response:
            headers = {key.casefold(): value for key, value in response.headers.items()}
            return int(response.status), headers, response.read()
    except HTTPError as exc:
        return int(exc.code), {key.casefold(): value for key, value in exc.headers.items()}, exc.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    app = root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"
    server_path = app / "study_server.py"
    source = server_path.read_text(encoding="utf-8")
    module = load_module(server_path)
    html_text = module.HTML
    checks: list[dict] = []

    def check(name: str, condition: bool, detail="") -> None:
        checks.append({"id": name, "ok": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    check("version_2b_2", module.APP_VERSION == "2B.2", module.APP_VERSION)
    check("controlled_research_desk_preserved", sha256(app / "research_desk.py") == EXPECTED_RESEARCH_DESK_SHA256)
    check("v1_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2.py") == EXPECTED_V1_2_VERIFIER_SHA256)
    check("v1_2_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2_2.py") == EXPECTED_V1_2_2_VERIFIER_SHA256)
    check("v2a_1_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V2A_1.py") == EXPECTED_V2A_1_VERIFIER_SHA256)
    check("v2b_1_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V2B_1.py") == EXPECTED_V2B_1_VERIFIER_SHA256)
    check("v2b_1_1_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V2B_1_1.py") == EXPECTED_V2B_1_1_VERIFIER_SHA256)

    required_backend = (
        "def epub_publication_package(", "def epub_reader_chapter(", "def epub_reader_asset(",
        "def save_epub_reader_state(", "def add_epub_bookmark(", "def continue_reading_ebooks(",
        "def detect_thorium_reader(", 'parsed.path == "/api/epub/reader"',
        'parsed.path == "/api/epub/chapter"', 'parsed.path == "/epub/asset"',
        'parsed.path == "/api/epub/reader/state"', 'parsed.path == "/api/epub/bookmark/add"',
        'parsed.path == "/api/epub/open-external"',
    )
    check("native_reader_backend_present", all(token in source for token in required_backend))
    check("reader_state_is_sidecar_only", "CREATE TABLE IF NOT EXISTS epub_reader_state" in source and "CREATE TABLE IF NOT EXISTS epub_bookmarks" in source)
    check("reader_safety_limits_present", all(token in source for token in ("EPUB_READER_MAX_ARCHIVE_BYTES", "EPUB_READER_MAX_CHAPTER_BYTES", "EPUB_READER_MAX_ASSET_BYTES", "EPUB_READER_MAX_COMPRESSION_RATIO")))
    check("voice_engine_not_activated", all(token not in source for token in ("speechSynthesis", "pyttsx3", "sapi.SpVoice", "edge_tts")))

    required_ui = (
        'id="epubReader"', 'id="epubReaderFrame"', "Read in Kayock's Study",
        "Back to Title Page", "Table of Contents", "Previous Chapter", "Next Chapter",
        "Start from Beginning", "Add Bookmark", "Continue Reading", "Read This to Me · V2B.3",
        "readerTheme", "readerFont", "readerTextSize", "readerLineSpacing", "readerContentWidth",
        "sandbox=\"allow-same-origin\"", "Content-Security-Policy", "openExternalEpub",
    )
    check("native_reader_ui_present", all(token in html_text for token in required_ui))
    check("v2b_1_1_title_pages_preserved", all(token in html_text for token in ("Summary", "My Rating", "How to Open", "Scan for New Books", "homeScanStatus")))
    check("reader_is_scriptless_sandbox", "allow-scripts" not in html_text and 'sandbox="allow-same-origin"' in html_text)
    check("external_reader_requires_explicit_action", 'data-detail-action="open-epub-external"' in html_text and "/api/epub/open-external" in html_text)

    tree = ast.parse(source)
    extracted = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "HTML" for target in node.targets):
            extracted = ast.literal_eval(node.value)
            break
    check("html_constant_extractable", extracted == html_text)
    check("single_script_block", html_text.count("<script>") == 1 and html_text.count("</script>") == 1)

    temp = Path(tempfile.mkdtemp(prefix="kayocks_study_v2b_2_http_"))
    server = None
    thread = None
    old_env = {key: os.environ.get(key) for key in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PATH")}
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
        pdf_path = paths.library / "Manuals" / "Fedora Reader Regression.pdf"
        pdf_path.parent.mkdir(parents=True)
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.add_metadata({"/Title": "Fedora Reader Regression", "/Subject": "PDF API preservation fixture."})
        with pdf_path.open("wb") as handle:
            writer.write(handle)

        epub_path = paths.library / "Fiction" / "Star Trek" / "V2B Test Set" / "Native Reader Fixture.epub"
        malformed_path = paths.library / "Fiction" / "Malformed Reader Fixture.epub"
        fixed_path = paths.library / "Fiction" / "Fixed Layout Fixture.epub"
        protected_path = paths.library / "Fiction" / "Protected Fixture.epub"
        make_reader_epub(epub_path)
        make_reader_epub(malformed_path, title="Malformed Reader Fixture", malformed_chapter=True)
        make_reader_epub(fixed_path, title="Fixed Layout Fixture", fixed_layout=True)
        make_encrypted_epub(protected_path)
        originals = {path.name: sha256(path) for path in (pdf_path, epub_path, malformed_path, fixed_path, protected_path)}

        indexed = module.index_library(paths)
        check("fixtures_cataloged", indexed.get("ok") is True and indexed.get("pdfs_found") == 1 and indexed.get("epubs_ready") == 3 and indexed.get("ebooks_needing_review") == 1, indexed)
        check("originals_unchanged_after_catalog", originals == {path.name: sha256(path) for path in (pdf_path, epub_path, malformed_path, fixed_path, protected_path)})

        ready = module.list_ebooks(paths, status="ready")
        by_title = {item["title"]: item for item in ready}
        reader_id = int(by_title["Reader Fixture"]["id"])
        malformed_id = int(by_title["Malformed Reader Fixture"]["id"])
        fixed_id = int(by_title["Fixed Layout Fixture"]["id"])

        publication = module.epub_publication_package(paths, reader_id)
        check("multi_chapter_spine", len(publication["spine"]) == 2, publication["spine"])
        check("nested_table_of_contents", publication["toc"] and publication["toc"][0].get("children"), publication["toc"])
        check("toc_assigns_chapter_titles", publication["spine"][0]["title"] == "Part One" and publication["spine"][1]["title"] == "Nested Chapter Two", publication["spine"])

        chapter = module.epub_reader_chapter(paths, reader_id, 0)
        lowered_html = chapter["html"].casefold()
        lowered_css = chapter["css"].casefold()
        check("chapter_text_and_styling_preserved", "chapter one" in lowered_html and "line-height" in lowered_css, {"html": chapter["html"][:300], "css": chapter["css"][:300]})
        check("scripts_and_event_handlers_blocked", "<script" not in lowered_html and "onclick" not in lowered_html and "onerror" not in lowered_html and "onload" not in lowered_html)
        check("forms_blocked", "<form" not in lowered_html and "<input" not in lowered_html and "<button" not in lowered_html)
        check("remote_resources_blocked", "evil.example" not in lowered_html and "evil.example" not in lowered_css and "https://" not in lowered_html and "https://" not in lowered_css)
        check("local_image_rewritten", "/epub/asset?id=" in chapter["html"] and "fixture image" in chapter["html"])
        check("internal_chapter_link_rewritten", "data-reader-target-member" in chapter["html"] and "chapter2.xhtml" in chapter["html"])
        check("embedded_font_and_image_urls_rewritten", chapter["css"].count("/epub/asset?id=") >= 2, chapter["css"])

        asset, media_type = module.epub_reader_asset(paths, reader_id, "OEBPS/Images/pixel.png")
        check("permitted_image_asset", asset == PIXEL_PNG and media_type == "image/png")
        font, font_type = module.epub_reader_asset(paths, reader_id, "OEBPS/Fonts/fixture.woff")
        check("permitted_embedded_font", font == b"fixture-font-bytes" and font_type == "font/woff")
        try:
            module.normalize_epub_member_request("../secret.txt")
        except ValueError:
            traversal_blocked = True
        else:
            traversal_blocked = False
        check("path_traversal_rejected", traversal_blocked)
        try:
            module.epub_reader_asset(paths, reader_id, "OEBPS/Text/chapter1.xhtml")
        except PermissionError:
            chapter_as_asset_blocked = True
        else:
            chapter_as_asset_blocked = False
        check("undeclared_asset_type_blocked", chapter_as_asset_blocked)

        malformed_chapter = module.epub_reader_chapter(paths, malformed_id, 0)
        check("malformed_html_fails_safely_and_keeps_text", "malformed but readable" in malformed_chapter["html"].casefold() and "<script" not in malformed_chapter["html"].casefold())
        try:
            module.epub_publication_package(paths, fixed_id)
        except ValueError as exc:
            fixed_refused = "Fixed-layout" in str(exc)
        else:
            fixed_refused = False
        check("fixed_layout_refused_with_fallback_guidance", fixed_refused)
        protected = [item for item in module.list_ebooks(paths) if item["title"] == "Protected Fixture"][0]
        try:
            module.epub_publication_package(paths, int(protected["id"]))
        except ValueError:
            protected_refused = True
        else:
            protected_refused = False
        check("encrypted_epub_refused", protected_refused)

        identity = module.epub_reader_identity(paths, reader_id)
        saved = module.save_epub_reader_state(paths, identity, {
            "spine_index": 1,
            "fragment": "destination",
            "scroll_ratio": 0.42,
            "preferences": {"theme": "sepia", "font": "sans", "text_size": 23, "line_spacing": 1.8, "content_width": 840},
        })
        check("reader_position_and_preferences_persist", saved["last_spine_index"] == 1 and saved["last_fragment"] == "destination" and saved["scroll_ratio"] == 0.42 and saved["preferences"]["theme"] == "sepia", saved)
        reread = module.epub_reader_state(paths, identity)
        check("reader_resume_round_trip", reread == saved, {"saved": saved, "reread": reread})
        bookmark = module.add_epub_bookmark(paths, identity, {"spine_index": 1, "fragment": "destination", "scroll_ratio": 0.42, "label": "Bridge Scene"})
        check("bookmark_created", bookmark["id"] > 0 and len(module.list_epub_bookmarks(paths, identity)) == 1, bookmark)
        check("bookmark_removed", module.remove_epub_bookmark(paths, identity, bookmark["id"]) and module.list_epub_bookmarks(paths, identity) == [])
        continue_items = module.continue_reading_ebooks(paths)
        check("continue_reading_shelf_data", continue_items and continue_items[0]["id"] == reader_id and continue_items[0]["last_spine_index"] == 1, continue_items)

        main_conn = module.connect_db(paths)
        try:
            main_tables = {row[0] for row in main_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            main_conn.close()
        epub_conn = module.connect_epub_db(paths)
        try:
            epub_tables = {row[0] for row in epub_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            epub_conn.close()
        state_conn = module.connect_library_state_db(paths)
        try:
            state_tables = {row[0] for row in state_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            state_conn.close()
        check("reader_tables_not_in_pdf_database", "epub_reader_state" not in main_tables and "epub_bookmarks" not in main_tables, sorted(main_tables))
        check("reader_tables_not_in_epub_catalog", "epub_reader_state" not in epub_tables and "epub_bookmarks" not in epub_tables, sorted(epub_tables))
        check("reader_tables_only_in_state_sidecar", {"epub_reader_state", "epub_bookmarks"}.issubset(state_tables), sorted(state_tables))

        fake_local = temp / "FakeLocalAppData"
        fake_thorium = fake_local / "Programs" / "Thorium" / "Thorium.exe"
        fake_thorium.parent.mkdir(parents=True)
        fake_thorium.write_bytes(b"fixture executable marker")
        os.environ["LOCALAPPDATA"] = str(fake_local)
        os.environ["PROGRAMFILES"] = str(temp / "NoProgramFiles")
        os.environ["PROGRAMFILES(X86)"] = str(temp / "NoProgramFilesX86")
        os.environ["PATH"] = ""
        detected = module.external_epub_reader_status()
        check("optional_thorium_detection", detected["mode"] == "thorium" and detected["label"] == "Open in Thorium", detected)
        fake_thorium.unlink()
        fallback = module.external_epub_reader_status()
        check("default_reader_fallback_label", fallback["mode"] == "default" and fallback["label"] == "Open in Default EPUB Reader", fallback)

        server = module.StudyServer(("127.0.0.1", 0), module.StudyHandler, paths)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        status, payload = request_json(base, "/api/epub/reader?" + urlencode({"id": reader_id}))
        check("reader_publication_http_200", status == 200 and len(payload.get("publication", {}).get("spine", [])) == 2, payload)
        status, payload = request_json(base, "/api/epub/chapter?" + urlencode({"id": reader_id, "index": 0}))
        check("sanitized_chapter_http_200", status == 200 and "evil.example" not in payload.get("chapter", {}).get("html", ""), payload)
        status, headers, body = request_bytes(base, "/epub/asset?" + urlencode({"id": reader_id, "path": "OEBPS/Images/pixel.png"}))
        check("asset_http_200", status == 200 and headers.get("content-type") == "image/png" and body == PIXEL_PNG, headers)
        status, _, _ = request_bytes(base, "/epub/asset?" + urlencode({"id": reader_id, "path": "../secret.txt"}))
        check("asset_path_traversal_http_refused", status == 403, status)
        status, payload = request_json(base, "/api/epub/reader/state", method="POST", payload={
            "id": reader_id, "spine_index": 0, "fragment": "start", "scroll_ratio": 0.25,
            "preferences": {"theme": "dark", "font": "serif", "text_size": 20, "line_spacing": 1.7, "content_width": 780},
        })
        check("reader_state_http_saved", status == 200 and payload.get("state", {}).get("scroll_ratio") == 0.25, payload)
        status, payload = request_json(base, "/api/epub/bookmark/add", method="POST", payload={"id": reader_id, "spine_index": 0, "scroll_ratio": 0.25, "label": "HTTP Bookmark"})
        http_bookmark_id = int(payload.get("bookmark", {}).get("id") or 0)
        check("bookmark_http_created", status == 200 and http_bookmark_id > 0, payload)
        status, payload = request_json(base, "/api/epub/bookmark/remove", method="POST", payload={"id": reader_id, "bookmark_id": http_bookmark_id})
        check("bookmark_http_removed", status == 200 and payload.get("removed") is True, payload)
        status, payload = request_json(base, "/api/epub/continue-reading")
        check("continue_reading_http_200", status == 200 and payload.get("ebooks"), payload)

        status, headers, body = request_bytes(base, "/epub/file?" + urlencode({"id": reader_id}))
        check("exact_original_external_fallback_handoff", status == 200 and hashlib.sha256(body).hexdigest() == originals[epub_path.name] and "attachment" in headers.get("content-disposition", "").casefold(), headers)

        status, payload = request_json(base, "/api/documents?include_review=0")
        check("pdf_documents_api_unchanged", status == 200 and len(payload.get("documents") or []) == 1, payload)
        status, payload = request_json(base, "/api/search?q=Fedora")
        check("pdf_search_api_still_json", status == 200 and payload.get("ok") is True and isinstance(payload.get("results"), list), payload)
        status, payload = request_json(base, "/api/library/item?kind=pdf&id=1")
        check("v2b_1_1_pdf_title_page_unchanged", status == 200 and payload.get("item", {}).get("source_kind") == "pdf", payload)
        status, payload = request_json(base, "/api/library/item?kind=epub&id=" + str(reader_id))
        check("v2b_1_1_epub_title_page_enhanced", status == 200 and payload.get("item", {}).get("reader_available") is True and payload.get("item", {}).get("original_epub_url"), payload)

        check("originals_unchanged_after_reader_tests", originals == {path.name: sha256(path) for path in (pdf_path, epub_path, malformed_path, fixed_path, protected_path)})
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=3)
        shutil.rmtree(temp, ignore_errors=True)

    receipt = {
        "schema": "foxai.kayocks_study.v2b_2.verification.v1",
        "mission": "Kayock's Study V2B.2 — Native In-App EPUB Reader",
        "result": "verified",
        "check_count": len(checks),
        "checks": checks,
        "safety": {
            "external_network_used": False,
            "loopback_http_only": True,
            "original_library_files_modified": 0,
            "bibliotheca_pdf_schema_changed": False,
            "epub_catalog_schema_changed": False,
            "reader_state_storage": "separate_local_sidecar",
            "scripts_forms_and_remote_resources_blocked": True,
            "voice_engine_added": False,
            "drm_removal_added": False,
            "external_reader_launched_during_verification": False,
        },
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
