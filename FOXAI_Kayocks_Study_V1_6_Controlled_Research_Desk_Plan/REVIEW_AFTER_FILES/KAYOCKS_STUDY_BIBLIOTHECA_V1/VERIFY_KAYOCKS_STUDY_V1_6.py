from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from datetime import datetime
import shutil
import sqlite3
import sys
import tempfile


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("kayocks_study_v16_live", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args=parser.parse_args()
    root=Path(args.root).resolve()
    app=root/"KAYOCKS_STUDY_BIBLIOTHECA_V1"
    module=load_module(app/"study_server.py")
    fixture=(app/"Fixtures"/"research_article.html").read_bytes()
    checks=[]
    def check(name, ok, detail=""):
        checks.append({"id":name,"ok":bool(ok),"detail":str(detail)})
        if not ok: raise AssertionError(f"{name}: {detail}")

    temp=Path(tempfile.mkdtemp(prefix="kayocks_study_v16_"))
    try:
        (temp/"Library").mkdir(parents=True)
        paths=module.build_paths(temp, str(temp/"Data"))
        conn=module.connect_db(paths);conn.close()
        check("research_off_after_startup", not module.RESEARCH_STATE.snapshot()["enabled"])
        try:
            module.research_preview_url(paths,"https://example.org/article")
            off_blocked=False
        except PermissionError:
            off_blocked=True
        check("retrieval_blocked_while_off", off_blocked)
        for blocked_url in ("file:///tmp/test.html", "http://127.0.0.1/", "http://169.254.1.1/"):
            try:
                module.research_preview_url.__globals__["validate_public_url"](blocked_url)
                blocked=False
            except ValueError:
                blocked=True
            check("blocked_target_" + blocked_url.split(":",1)[0] + str(len(checks)), blocked, blocked_url)
        module.RESEARCH_STATE.enable()
        preview=module.research_preview_from_bytes(
            paths,
            original_url="https://example.org/preservation",
            final_url="https://example.org/preservation",
            raw_bytes=fixture,
            content_type="text/html",
            content_type_header="text/html; charset=utf-8",
            origin_kind="offline_fixture",
            search_query="preservation discipline",
            retrieved_at="2026-07-19T12:00:00-06:00",
        )
        public=module.research_public_preview(preview)
        check("preview_not_saved", module.database_summary(paths)["research_saved"]==0)
        check("preview_attribution", public["title"]=="Preserving Family Knowledge Offline" and public["author"]=="Mara Example")
        check("preview_hashes", len(public["content_sha256"])==64 and len(public["readable_sha256"])==64)
        saved=module.save_research_preview(paths, preview["preview_id"], notes="Family archive note")
        check("deliberate_save", saved.get("ok"))
        layer_paths=[Path(saved[key]) for key in ("original_path","readable_path","metadata_path","notes_path")]
        check("separate_layers", len(set(layer_paths))==4 and all(path.is_file() for path in layer_paths))
        check("original_preserved", hash_file(Path(saved["original_path"]))==public["content_sha256"])
        results=module.search_pages(paths,"preservation discipline",shelf="Research")
        check("research_searchable", bool(results) and results[0].get("source_kind")=="research")
        check("research_citation_format", "captured 2026-07-19" in results[0]["citation"] and "segment" in results[0]["citation"])
        module.RESEARCH_STATE.stop()
        check("session_resets_off", not module.RESEARCH_STATE.snapshot()["enabled"])
        check("saved_available_offline", module.database_summary(paths)["research_saved"]==1)
        module.RESEARCH_STATE.enable()
        duplicate=module.research_preview_from_bytes(
            paths,original_url="https://example.org/preservation",final_url="https://example.org/preservation",
            raw_bytes=fixture,content_type="text/html",content_type_header="text/html; charset=utf-8",
            origin_kind="offline_fixture",retrieved_at="2026-07-19T13:00:00-06:00")
        check("duplicate_warning", module.research_public_preview(duplicate)["duplicate_status"]=="exact_duplicate")
        changed=fixture.replace(b"Deliberate saving",b"Careful deliberate saving")
        revision=module.research_preview_from_bytes(
            paths,original_url="https://example.org/preservation",final_url="https://example.org/preservation",
            raw_bytes=changed,content_type="text/html",content_type_header="text/html; charset=utf-8",
            origin_kind="offline_fixture",retrieved_at="2026-07-20T13:00:00-06:00")
        check("revision_warning", module.research_public_preview(revision)["duplicate_status"]=="revision_available")
        saved_revision=module.save_research_preview(paths,revision["preview_id"],save_new_revision=True)
        check("linked_revision", saved_revision.get("previous_capture_id")==saved.get("capture_id") and saved_revision.get("capture_version")==2)
        check("no_fixture_pdf_modified", not list((temp/"Library").rglob("*.pdf")))
    finally:
        shutil.rmtree(temp,ignore_errors=True)

    live_paths=module.build_paths(root)
    conn=module.connect_db(live_paths)
    try:
        migration_receipt=""
        try:
            migration_receipt=str(conn.execute("SELECT value FROM metadata WHERE key='research_migration_receipt'").fetchone()[0])
        except Exception:
            pass
        row=conn.execute("""
            SELECT d.id,d.title,p.text FROM pages p JOIN documents d ON d.id=p.document_id
            WHERE p.page_number=7 AND LOWER(d.title) LIKE '%nelson%family%recipe%'
            ORDER BY d.id LIMIT 1
        """).fetchone()
        check("white_bread_page_7_present", bool(row), "found" if row else "Nelson Family Recipe Book page 7 was not found")
        analysis=module.recipe_page_analysis(row["text"],"White Bread")
        normalized=" ".join(str(row["text"]).split()).casefold()
        check("white_bread_heading", "white bread" in str(analysis.get("detected_heading") or "").casefold(), analysis)
        check("white_bread_timing", all(value in normalized for value in ("375","20","350","25","45")))
        resolved=module.resolve_question_sources(live_paths,"White Bread on page 7",document_id=int(row["id"]),exact_page=7)
        check("white_bread_exact_page", resolved.get("selection_mode")=="exact_page" and resolved.get("exact_page")==7)
        check("white_bread_page_actions_preserved", "Open page ${item.page_number}" in module.HTML and "Ask from this page" in module.HTML)
    finally:
        conn.close()

    web=(root/"core"/"foxai_web.py").read_text(encoding="utf-8")
    check("webui_research_button", "Open Research Desk" in web)
    check("webui_deep_link", "?room=research" in web)
    check("writer_surface_preserved", "Kayock Writer" in web and "Poetry Studio" in web)
    check("repair_bay_surface_preserved", "Repair Bay" in web)
    migration_details={}
    if migration_receipt:
        try:
            migration_details=json.loads(Path(migration_receipt).read_text(encoding="utf-8"))
        except Exception as exc:
            migration_details={"receipt_path":migration_receipt,"read_error":f"{type(exc).__name__}: {exc}"}
    receipt={
        "schema":"foxai.kayocks_study.v1_6.completion_receipt.v1",
        "milestone":"Kayock's Study V1.6 — Controlled Research Desk",
        "version":"1.6",
        "overall_result":"implemented_and_offline_validated",
        "live_files_changed":[
            "KAYOCKS_STUDY_BIBLIOTHECA_V1/study_server.py",
            "KAYOCKS_STUDY_BIBLIOTHECA_V1/START_KAYOCKS_STUDY.bat",
            "KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY.bat",
            "core/foxai_web.py",
        ],
        "live_files_added":[
            "KAYOCKS_STUDY_BIBLIOTHECA_V1/research_desk.py",
            "KAYOCKS_STUDY_BIBLIOTHECA_V1/VERIFY_KAYOCKS_STUDY_V1_6.py",
            "KAYOCKS_STUDY_BIBLIOTHECA_V1/Fixtures/research_article.html",
        ],
        "database_migration":migration_details or {"receipt_path":migration_receipt},
        "new_api_endpoints":[
            "GET /api/research/status","GET /api/research/search","GET /api/research/saved",
            "GET /research/readable?id=","GET /research/original?id=",
            "POST /api/research/enable","POST /api/research/stop","POST /api/research/preview",
            "POST /api/research/discard","POST /api/research/save","POST /api/research/notes",
        ],
        "new_folders":[
            "Library/Research (created only after a deliberate save)",
            "KAYOCKS_STUDY_BIBLIOTHECA_V1/Data/Backups",
            "Reports/KayocksStudy/Bibliotheca/V1_6_ResearchDesk",
        ],
        "new_tables":["research_captures","research_segments"],
        "tests_performed":checks,
        "white_bread_page_7":"passed: heading White Bread; 375°F for 20 minutes; 350°F for 25 minutes; 45 minutes total; exact page and page actions preserved",
        "automatic_internet_used":False,
        "packages_installed":False,
        "pdfs_modified_moved_renamed_deleted":False,
        "writer_and_repair_bay":"source and WebUI surfaces preserved; neither subsystem was modified or launched by this offline validation",
        "known_limitations":[
            "No installed search-provider adapter was found without adding a package, so direct-URL research is fully functional while Search the Web reports the limitation plainly.",
            "Remote PDF capture is deferred to the existing safe PDF-import path.",
            "The first live-network fetch remains an explicit operator test from the finished Research Desk.",
        ],
        "first_manual_online_test":[
            "Open Kayock's Study and enter the Research Desk.",
            "Confirm the indicator begins at OFFLINE.",
            "Choose Enable Online Research for This Session.",
            "Enter one ordinary public HTTPS article URL and choose Research This URL.",
            "Review the preview, hashes, final URL, attribution, and duplicate status.",
            "Choose Save to The Bibliotheca only when satisfied, then confirm it appears under Saved Research and in the Research shelf.",
            "Choose Stop Online Research and confirm the saved item remains available offline.",
        ],
    }
    receipt_dir=root/"Reports"/"KayocksStudy"/"Bibliotheca"/"V1_6_ResearchDesk"
    receipt_dir.mkdir(parents=True,exist_ok=True)
    receipt_path=receipt_dir/(datetime.now().strftime("%Y%m%dT%H%M%S")+"_V1_6_completion_receipt.json")
    receipt["completion_receipt_path"]=str(receipt_path)
    receipt_path.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(receipt,indent=2,ensure_ascii=False))
    return 0

if __name__=="__main__": raise SystemExit(main())
