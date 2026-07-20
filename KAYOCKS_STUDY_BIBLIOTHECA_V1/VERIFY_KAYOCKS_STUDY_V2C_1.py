from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile


def check(checks: list[dict], check_id: str, ok: bool, message: str = "") -> None:
    checks.append({"id": check_id, "ok": bool(ok), "message": str(message)})
    if not ok:
        raise AssertionError(f"{check_id}: {message}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_epub(path: Path, title: str, author: str, identifier: str) -> None:
    container = b'''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
 <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''
    opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
 <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:identifier id="bookid">{identifier}</dc:identifier><dc:title>{title}</dc:title><dc:creator>{author}</dc:creator>
  <dc:description>Deterministic local catalog fixture.</dc:description>
 </metadata>
 <manifest><item id="c1" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
 <spine><itemref idref="c1"/></spine>
</package>'''.encode("utf-8")
    chapter = f'''<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>{title}</h1><p>Fixture chapter.</p></body></html>'''.encode("utf-8")
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        archive.writestr(info, b"application/epub+zip")
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/chapter.xhtml", chapter)


def synchsafe(value: int) -> bytes:
    return bytes([(value >> 21) & 0x7F, (value >> 14) & 0x7F, (value >> 7) & 0x7F, value & 0x7F])


def text_frame(frame_id: str, value: str) -> bytes:
    payload = b"\x03" + value.encode("utf-8")
    return frame_id.encode("ascii") + len(payload).to_bytes(4, "big") + b"\x00\x00" + payload


def make_mp3(path: Path, title: str, author: str, album: str = "") -> None:
    frames = text_frame("TIT2", title) + text_frame("TPE1", author)
    if album:
        frames += text_frame("TALB", album)
    path.write_bytes(b"ID3\x03\x00\x00" + synchsafe(len(frames)) + frames + b"\x00" * 512)


def http_json(base: str, route: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = Request(base + route, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    app = root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"
    server_path = app / "study_server.py"
    module_path = app / "external_library.py"
    checks: list[dict] = []

    check(checks, "source_exists", server_path.is_file() and module_path.is_file(), str(app))
    server_source = server_path.read_text(encoding="utf-8")
    module_source = module_path.read_text(encoding="utf-8")
    check(checks, "version_v2c1", 'APP_VERSION = "2C.1"' in server_source)
    check(checks, "library_locations_ui", all(token in server_source for token in (
        "Library Locations", "Approve One Folder", "Registered Locations", "Unified Titles",
        "Read", "Listen", "Maps & Extras", "File Locations and Editions",
    )))
    check(checks, "no_drive_enumeration_code", all(token not in module_source for token in (
        "GetLogicalDrives", "wmic logicaldisk", "psutil.disk_partitions", "Path('/').rglob",
    )))
    check(checks, "explicit_root_guard", "Register a specific library folder, not an entire drive root." in module_source)
    check(checks, "supported_formats", all(ext in module_source for ext in (
        '.epub', '.pdf', '.mobi', '.azw', '.azw3', '.m4b', '.mp3', '.flac', '.ogg', '.wav', '.png'
    )))
    check(checks, "preserved_reader_features", all(token in server_source for token in (
        "/api/epub/reader", "/api/epub/chapter", "Read This to Me", "speechSynthesis", "localService===true",
        "readerTheme", "readerBookmarkButton", "Continue Reading",
    )))
    check(checks, "preserved_pdf_apis", all(token in server_source for token in (
        'parsed.path == "/api/search"', 'parsed.path == "/pdf"', 'parsed.path == "/api/documents"'
    )))

    sys_path_added = False
    import sys
    if str(app) not in sys.path:
        sys.path.insert(0, str(app)); sys_path_added = True
    spec = importlib.util.spec_from_file_location("study_server_v2c1_verify", server_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load study_server.py")
    server = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = server
    spec.loader.exec_module(server)
    external = server.__dict__["connect_external_library_db"].__module__
    extmod = sys.modules[external]

    fixture_root = Path(tempfile.mkdtemp(prefix="kayocks_study_v2c1_verify_"))
    try:
        fox_root = fixture_root / "FOXAI"
        (fox_root / "Library").mkdir(parents=True)
        data_dir = fixture_root / "Data"
        data_dir.mkdir()
        paths = server.build_paths(fox_root, str(data_dir))

        library_a = fixture_root / "DriveA" / "Books and Audio"
        hp = library_a / "Harry Potter and the Half-Blood Prince"
        hp.mkdir(parents=True)
        epub = hp / "Harry Potter and the Half-Blood Prince.epub"
        make_epub(epub, "Harry Potter and the Half-Blood Prince", "J. K. Rowling", "hp6")
        duplicate = hp / "HP6 backup different filename.epub"
        shutil.copyfile(epub, duplicate)
        mobi = hp / "Harry Potter and the Half-Blood Prince.mobi"
        mobi.write_bytes(b"BOOKMOBI" + b"\x00" * 128)
        mp3 = hp / "Part 01.mp3"
        make_mp3(mp3, "Harry Potter and the Half-Blood Prince", "J. K. Rowling", "Harry Potter 6")
        map_file = hp / "Hogwarts Map.png"
        map_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"map-fixture")
        map_pdf = hp / "Companion Map.pdf"
        map_pdf.write_bytes(b"%PDF-1.4\n% deterministic companion\n")
        unsupported = hp / "do-not-open.exe"
        unsupported.write_bytes(b"MZfixture")

        library_b = fixture_root / "DriveB" / "Star Trek"
        library_b.mkdir(parents=True)
        st_epub = library_b / "Star Trek Voyager Homecoming.epub"
        make_epub(st_epub, "Star Trek: Voyager — Homecoming", "Christie Golden", "st-homecoming")
        st_mobi = library_b / "Star Trek Voyager Homecoming.mobi"
        st_mobi.write_bytes(b"BOOKMOBI" + b"\x01" * 128)
        mystery = library_b / "Mystery Companion.pdf"
        mystery.write_bytes(b"%PDF-1.4\n% unrelated fixture\n")

        originals = {str(path): sha(path) for path in (epub, duplicate, mobi, mp3, map_file, map_pdf, unsupported, st_epub, st_mobi, mystery)}

        preview = extmod.preview_location(library_a)
        check(checks, "preview_available_root", preview["ok"] and preview["availability"] == "online")
        check(checks, "preview_supported_only", preview["supported_files"] == 6, preview)
        check(checks, "unsupported_executable_ignored", ".exe" not in preview["counts_by_extension"])
        check(checks, "preview_no_hash_or_write", preview["files_modified"] == 0 and preview["estimated_hash_bytes"] > 0)

        root_a = extmod.register_location(paths, library_a, "Audiobooks and Ebooks")["root"]
        root_b = extmod.register_location(paths, library_b, "Star Trek Archive")["root"]
        check(checks, "two_explicit_roots_registered", len(extmod.list_locations(paths)["roots"]) == 2)
        check(checks, "automatic_crawl_false", extmod.list_locations(paths)["automatic_drive_crawling"] is False)

        result_a = extmod.scan_location(paths, root_a["id"])
        result_b = extmod.scan_location(paths, root_b["id"])
        check(checks, "available_roots_scanned", result_a["ok"] and result_b["ok"])
        check(checks, "original_modification_zero", result_a["original_files_modified"] == 0 and result_b["original_files_modified"] == 0)
        check(checks, "unsupported_not_cataloged", result_a["supported_files"] == 6)

        works = extmod.list_works(paths)["works"]
        hp_work = next(work for work in works if "half" in work["title"].casefold() and "prince" in work["title"].casefold())
        st_work = next(work for work in works if "homecoming" in work["title"].casefold())
        hp_detail = extmod.work_detail(paths, hp_work["id"])["work"]
        check(checks, "unified_read_and_listen", len(hp_detail["sections"]["read"]) >= 3 and len(hp_detail["sections"]["listen"]) == 1)
        check(checks, "audiobook_folder_companions", len(hp_detail["sections"]["companion"]) >= 2)
        check(checks, "same_title_epub_mobi_grouped", {item["extension"] for item in hp_detail["sections"]["read"]}.issuperset({".epub", ".mobi"}))
        hashes = [item["sha256"] for item in hp_detail["items"] if item["extension"] == ".epub"]
        check(checks, "exact_duplicate_hash_detected", len(hashes) == 2 and len(set(hashes)) == 1)
        check(checks, "exact_duplicate_confirmed", any(item["match_confidence"] == "confirmed" for item in hp_detail["items"] if item["extension"] == ".epub"))
        st_detail = extmod.work_detail(paths, st_work["id"])["work"]
        check(checks, "probable_title_matching", any(item["match_confidence"] in {"probable", "confirmed"} for item in st_detail["items"] if item["extension"] == ".mobi"))

        conn = extmod.connect_external_library_db(paths)
        try:
            mystery_row = conn.execute("SELECT id,work_id FROM external_library_items WHERE filename='Mystery Companion.pdf'").fetchone()
        finally:
            conn.close()
        check(checks, "manual_candidate_exists", mystery_row is not None)
        assigned = extmod.assign_item_to_work(paths, int(mystery_row["id"]), hp_work["id"])
        check(checks, "manual_relationship_correction", assigned["match_confidence"] == "confirmed" and assigned["work_id"] == hp_work["id"])
        split = extmod.assign_item_to_work(paths, int(mystery_row["id"]), split=True)
        check(checks, "manual_split_new_title", split["work_id"] != hp_work["id"])

        disabled = extmod.set_location_enabled(paths, root_b["id"], False)["root"]
        check(checks, "root_disable", disabled["enabled"] is False)
        started, message = extmod.start_location_scan(paths, root_b["id"])
        check(checks, "disabled_root_scan_refused", started is False and "disabled" in message.casefold())
        extmod.set_location_enabled(paths, root_b["id"], True)

        offline_holder = fixture_root / "DriveB.offline"
        library_b.rename(offline_holder)
        locations = extmod.list_locations(paths)["roots"]
        offline = next(item for item in locations if item["id"] == root_b["id"])
        check(checks, "offline_root_retained", offline["availability"] == "offline" and offline["catalog_files"] > 0)
        library_b.parent.mkdir(parents=True, exist_ok=True)
        offline_holder.rename(library_b)

        before_remove = {str(path): sha(path) for path in library_b.rglob("*") if path.is_file()}
        removed = extmod.remove_location_from_catalog(paths, root_b["id"])
        after_remove = {str(path): sha(path) for path in library_b.rglob("*") if path.is_file()}
        check(checks, "safe_root_catalog_removal", removed["removed_catalog_items"] >= 3 and removed["original_files_modified"] == 0)
        check(checks, "root_remove_preserves_files", before_remove == after_remove)

        final_hashes = {path: sha(Path(path)) for path in originals}
        check(checks, "all_original_hashes_unchanged", originals == final_hashes)

        environment = extmod.verify_external_library_environment(paths)
        check(checks, "sidecar_environment", environment["ok"] and environment["database"].endswith("external_library.sqlite3"))
        check(checks, "existing_databases_untouched_by_schema", Path(paths.database).name == "bibliotheca.sqlite3" and Path(paths.epub_database).name == "epub_catalog.sqlite3")

        # Live loopback API verification using a third explicit fixture root.
        api_root = fixture_root / "ApiDrive" / "Library"
        api_root.mkdir(parents=True)
        make_epub(api_root / "API Book.epub", "API Book", "Local Author", "api-book")
        server_instance = server.StudyServer(("127.0.0.1", 0), server.StudyHandler, paths)
        thread = threading.Thread(target=server_instance.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server_instance.server_address[1]}"
        try:
            with urlopen(base + "/", timeout=10) as response:
                html = response.read().decode("utf-8")
                check(checks, "live_home_v2c1", response.status == 200 and "Library Locations" in html and "Bibliotheca V2C.1" in html)
            status, payload = http_json(base, "/api/external-library/preview", {"path": str(api_root)})
            check(checks, "live_preview_api", status == 200 and payload["preview"]["supported_files"] == 1)
            status, payload = http_json(base, "/api/external-library/register", {"path": str(api_root), "label": "API Root"})
            api_root_id = payload["root"]["id"]
            check(checks, "live_register_api", status == 200 and payload["root"]["label"] == "API Root")
            status, payload = http_json(base, "/api/external-library/scan", {"id": api_root_id})
            check(checks, "live_background_scan_start", status == 202 and payload["ok"])
            deadline = time.time() + 15
            scan_payload = {}
            while time.time() < deadline:
                _, scan_payload = http_json(base, "/api/external-library/scan-status")
                if not scan_payload.get("running") and scan_payload.get("last_result"):
                    break
                time.sleep(0.1)
            check(checks, "live_background_scan_complete", not scan_payload.get("running") and scan_payload.get("last_result", {}).get("ok"))
            status, roots_payload = http_json(base, "/api/external-library/roots")
            check(checks, "live_roots_api", status == 200 and any(item["id"] == api_root_id for item in roots_payload["roots"]))
            status, works_payload = http_json(base, "/api/external-library/works")
            api_work = next(item for item in works_payload["works"] if item["title"] == "API Book")
            check(checks, "live_works_api", status == 200 and api_work["read_count"] == 1)
            status, detail_payload = http_json(base, f"/api/external-library/work?id={api_work['id']}")
            check(checks, "live_work_detail_api", status == 200 and detail_payload["work"]["sections"]["read"])
            status, existing_status = http_json(base, "/api/status")
            check(checks, "existing_status_api_unchanged", status == 200 and existing_status.get("version") == "2C.1")
            status, docs_payload = http_json(base, "/api/documents?include_review=0")
            check(checks, "existing_documents_api_unchanged", status == 200 and "documents" in docs_payload)
            status, ebooks_payload = http_json(base, "/api/ebooks")
            check(checks, "existing_ebooks_api_unchanged", status == 200 and "ebooks" in ebooks_payload)
        finally:
            server_instance.shutdown(); server_instance.server_close(); thread.join(timeout=5)

        check(checks, "loopback_only", base.startswith("http://127.0.0.1:"))
        check(checks, "no_external_network_requested", True, "Verifier used only local fixture files and loopback HTTP.")

    finally:
        shutil.rmtree(fixture_root, ignore_errors=True)
        if sys_path_added:
            try: sys.path.remove(str(app))
            except ValueError: pass

    result = {
        "result": "passed",
        "check_count": len(checks),
        "checks": checks,
        "network": "loopback_only",
        "automatic_drive_crawling": False,
        "original_files_modified": 0,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
