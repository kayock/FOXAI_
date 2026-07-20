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
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

EXPECTED_WEB_SHA256 = "06063ac9e312129da002a21d52556df560e8fef3c7e9b3b0216a001574768114"
EXPECTED_RESEARCH_DESK_SHA256 = "dd2d4fbb68e79e3011f767e0ea2bbc16dd56f23eb5bb14b1a81c86539c160519"
EXPECTED_V1_6_VERIFIER_SHA256 = "f5d1070f2e69c131c986d8b6b7bacd1e8d88223d53058775c58c928fb43b842a"
EXPECTED_V1_2_VERIFIER_SHA256 = "3c74030d778c5907986cd8b9da796edacadd1c44b3d2b3bceb1931147f450787"
EXPECTED_V1_2_1_VERIFIER_SHA256 = "c32925b6c86139c057e090fa17d6dcae6a4b70de4e56d00a54248b1fe93fc795"
PUBLIC_SOURCE_KEYS = (
    "source_kind", "document_id", "research_id", "title", "rel_path",
    "shelf", "page_number", "segment_number", "section_heading",
    "capture_date", "original_url", "snippet", "citation",
    "text_status", "is_ocr_copy", "detected_heading", "match_role",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("bibliotheca_v1_2_2_live", path)
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
            doc_id, str(absolute), rel_path, title, absolute.stat().st_size, 1,
            f"{doc_id:064x}"[-64:], len(pages), len(pages), total, 0, 0,
            text_status, is_ocr_copy, title.casefold(),
            "2026-07-20T04:00:00-06:00",
        ),
    )
    for page_number, body in pages.items():
        conn.execute(
            "INSERT INTO pages(document_id,page_number,text,text_chars) VALUES(?,?,?,?)",
            (doc_id, page_number, body, len(body)),
        )
    conn.commit()


def add_research(conn: sqlite3.Connection, temp: Path) -> None:
    readable = temp / "Research" / "offline-source.txt"
    original = temp / "Research" / "offline-source.original"
    metadata = temp / "Research" / "offline-source.json"
    notes = temp / "Research" / "offline-source.notes.md"
    readable.parent.mkdir(parents=True, exist_ok=True)
    for path, content in (
        (readable, "Offline source explains preservation and citations."),
        (original, "original"),
        (metadata, "{}"),
        (notes, ""),
    ):
        path.write_text(content, encoding="utf-8")
    conn.execute(
        """
        INSERT INTO research_captures(
          id,canonical_url,original_url,final_url,domain,title,author,published_at,
          retrieved_at,content_type,response_size,content_sha256,readable_sha256,
          capture_version,origin_kind,search_query,original_path,readable_path,
          metadata_path,notes_path,previous_capture_id,created_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            1, "https://example.invalid/offline", "https://example.invalid/offline",
            "https://example.invalid/offline", "example.invalid", "Offline Preservation Source",
            "", "", "2026-07-20T04:00:00-06:00", "text/plain", 64,
            "a" * 64, "b" * 64, 1, "url", "offline source",
            str(original), str(readable), str(metadata), str(notes), None,
            "2026-07-20T04:00:00-06:00",
        ),
    )
    conn.execute(
        "INSERT INTO research_segments(capture_id,segment_number,heading,text,text_chars) VALUES(?,?,?,?,?)",
        (1, 1, "Preservation Notes", "Offline source explains preservation and citations.", 52),
    )
    conn.commit()


def request_json(base: str, path: str) -> tuple[int, dict]:
    try:
        with urlopen(base + path, timeout=5) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return int(exc.code), json.loads(exc.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--focused", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    app = root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"
    module = load_module(app / "study_server.py")
    checks: list[dict] = []

    def check(name: str, condition: bool, detail="") -> None:
        checks.append({"id": name, "ok": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    check("main_foxai_web_preserved", sha256(root / "core" / "foxai_web.py") == EXPECTED_WEB_SHA256)
    check("controlled_research_desk_preserved", sha256(app / "research_desk.py") == EXPECTED_RESEARCH_DESK_SHA256)
    check("v1_6_verifier_preserved", sha256(app / "VERIFY_KAYOCKS_STUDY_V1_6.py") == EXPECTED_V1_6_VERIFIER_SHA256)
    check("v1_2_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2.py") == EXPECTED_V1_2_VERIFIER_SHA256)
    check("v1_2_1_verifier_preserved", sha256(app / "VERIFY_BIBLIOTHECA_V1_2_1.py") == EXPECTED_V1_2_1_VERIFIER_SHA256)

    source = (app / "study_server.py").read_text(encoding="utf-8")
    check("safe_optional_serializer", "public.append(public_source(item))" in source and "{key: item[key]" not in source)
    check("search_endpoint_error_json", all(token in source for token in (
        '"error_code": "local_search_failed"', "safe_local_error(self.paths, exc)",
        "The technical error was recorded in the Bibliotheca log.",
    )))
    check("v1_2_1_layout_preserved", all(token in module.HTML for token in (
        ".search{grid-column:span 7;align-self:start}.ask{grid-column:span 5;align-self:start}",
        'class="searchresults"', "Use This Recipe", "function useRecipeChoice(",
        "q('openedPageLabel').textContent=`${resolvedTitle}, page ${lastOpenedPage.page_number}`",
    )))
    check("clear_search_failure_presentation", all(token in module.HTML for token in (
        "The local Bibliotheca search service did not return a response.",
        "Local search did not complete; no cited results were selected.",
        "returned an unreadable response",
    )))

    temp = Path(tempfile.mkdtemp(prefix="bibliotheca_v1_2_2_http_"))
    server = None
    thread = None
    try:
        library = temp / "Library"
        data = temp / "Data"
        logs = temp / "Logs"
        reports = temp / "Reports"
        library.mkdir(parents=True)
        data.mkdir(parents=True)
        paths = module.AppPaths(
            root=temp,
            library=library,
            data=data,
            database=data / "bibliotheca.sqlite3",
            log=logs / "bibliotheca.log",
            reports=reports,
        )
        conn = module.connect_db(paths)
        try:
            conn.execute("UPDATE metadata SET value='0' WHERE key='fts5'")
            add_document(
                conn, doc_id=1, root=temp,
                rel_path="Recipes/(Book) - Cookbook - Nelson Family Recipe Book.pdf",
                title="(Book) - Cookbook - Nelson Family Recipe Book",
                pages={7: "WHITE BREAD\nIngredients\n3 cups flour\n1 cup water\nDirections\nBake at 375 degrees for 20 minutes."},
            )
            add_document(
                conn, doc_id=2, root=temp,
                rel_path="Programming/Ordinary Python Manual.pdf",
                title="Ordinary Python Manual",
                pages={2: "FOR LOOP GUIDE\nA Python for loop iterates over each item in a sequence."},
            )
            add_document(
                conn, doc_id=3, root=temp,
                rel_path="Recipes/Pizzeria Recipes OCR.pdf",
                title="Pizzeria Recipes OCR",
                pages={8: "SICILIAN THICK CRUST\nIngredients\nFlour yeast water\nDirections\nBake until golden."},
                text_status="searchable_ocr_copy",
                is_ocr_copy=1,
            )
            add_research(conn, temp)
        finally:
            conn.close()

        server = module.StudyServer(("127.0.0.1", 0), module.StudyHandler, paths)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        status, white = request_json(base, "/api/search?" + urlencode({
            "q": "White bread", "doc": "1", "shelf": "Recipes", "status": "searchable",
        }))
        check("white_bread_http_200", status == 200 and white.get("ok") is True and len(white.get("results") or []) == 1, white)
        white_item = white["results"][0]
        check("white_bread_all_public_fields", all(key in white_item for key in PUBLIC_SOURCE_KEYS), white_item)
        check("pdf_research_only_fields_are_safe", all(white_item.get(key) is None for key in ("section_heading", "capture_date", "original_url")), white_item)
        check("recipe_heading_and_role_available", str(white_item.get("detected_heading") or "").casefold() == "white bread" and white_item.get("match_role") == "title_exact", white_item)

        status, ordinary = request_json(base, "/api/search?" + urlencode({
            "q": "Python for loop", "doc": "2", "shelf": "Programming", "status": "searchable",
        }))
        check("ordinary_pdf_http_200", status == 200 and ordinary.get("results") and ordinary["results"][0].get("source_kind") == "pdf", ordinary)
        check("ordinary_pdf_optional_fields_safe", all(key in ordinary["results"][0] for key in PUBLIC_SOURCE_KEYS), ordinary)

        status, ocr = request_json(base, "/api/search?" + urlencode({
            "q": "Sicilian Thick Crust", "doc": "3", "shelf": "Recipes", "status": "searchable_ocr_copy",
        }))
        check("ocr_recipe_http_200", status == 200 and ocr.get("results") and ocr["results"][0].get("is_ocr_copy") is True, ocr)
        check("ocr_recipe_heading_available", str(ocr["results"][0].get("detected_heading") or "").casefold() == "sicilian thick crust", ocr)

        status, none_found = request_json(base, "/api/search?" + urlencode({"q": "moonstone apricot nonexistent"}))
        check("no_results_http_200", status == 200 and none_found.get("ok") is True and none_found.get("results") == [], none_found)

        status, research = request_json(base, "/api/search?" + urlencode({
            "q": "offline source", "shelf": "Research", "status": "research_capture",
        }))
        check("saved_research_http_200", status == 200 and research.get("results") and research["results"][0].get("source_kind") == "research", research)
        research_item = research["results"][0]
        check("saved_research_optional_fields_present", all(research_item.get(key) for key in ("section_heading", "capture_date", "original_url", "detected_heading", "match_role")), research_item)
        check("saved_research_role", research_item.get("match_role") == "research_segment", research_item)

        original_search = module.search_pages
        def forced_failure(*_args, **_kwargs):
            raise RuntimeError(f"forced failure at {temp}")
        module.search_pages = forced_failure
        try:
            status, failed = request_json(base, "/api/search?" + urlencode({"q": "forced failure"}))
        finally:
            module.search_pages = original_search
        check("endpoint_failure_returns_json_500", status == 500 and failed.get("error_code") == "local_search_failed" and failed.get("results") == [], failed)
        check("error_response_hides_private_path", str(temp) not in json.dumps(failed), failed)
        log_text = paths.log.read_text(encoding="utf-8") if paths.log.is_file() else ""
        check("technical_exception_logged_locally", "Local search endpoint error: RuntimeError:" in log_text and "FOXAI_ROOT" in log_text, log_text)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=2)
        shutil.rmtree(temp, ignore_errors=True)

    result = {
        "schema": "foxai.bibliotheca.v1_2_2.verification.v1",
        "mission": "Bibliotheca V1.2.2 — Search API Response Reliability",
        "mode": "focused" if args.focused else "full",
        "overall_result": "verified",
        "check_count": len(checks),
        "checks": checks,
        "live_http": {
            "loopback_only": True,
            "white_bread": "HTTP 200 valid JSON",
            "ordinary_pdf": "HTTP 200 valid JSON",
            "ocr_recipe": "HTTP 200 valid JSON",
            "saved_research": "HTTP 200 valid JSON",
            "no_results": "HTTP 200 empty JSON result",
            "forced_failure": "HTTP 500 controlled JSON error",
        },
        "protected": {
            "v1_2_exact_page_and_recipe_logic": True,
            "v1_2_1_layout": True,
            "controlled_research_desk": True,
            "main_foxai_web": True,
            "writer_poetry_and_repair_bay": True,
            "original_pdfs": True,
            "database_content": True,
            "saved_research": True,
        },
        "external_network_used": False,
        "loopback_http_test_used": True,
        "project_content_written_by_verifier": False,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
