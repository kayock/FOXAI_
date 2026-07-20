from __future__ import annotations
import argparse, ast, hashlib, importlib.util, json, os, sqlite3, subprocess, sys, tempfile, zipfile
from pathlib import Path
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("kayocks_study_v2b3_live", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_epub(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    container = '''<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
    package = '''<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier>urn:v2b3:test</dc:identifier><dc:title>Narration Fixture</dc:title><dc:creator>Local Voice Tester</dc:creator><dc:language>en-US</dc:language><dc:description>A fixture for local narration.</dc:description></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="chapter2.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>'''
    nav = '''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li><a href="chapter1.xhtml">One</a></li><li><a href="chapter2.xhtml">Two</a></li></ol></nav></body></html>'''
    c1 = '''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>One</title></head><body><h1>Chapter One</h1><p>First paragraph for narration.</p><blockquote>A meaningful quotation.</blockquote><hr/><p hidden="hidden">Hidden words must not be narrated.</p><img alt="A starship crossing a field of bright stars" src="missing.png"/></body></html>'''
    c2 = '''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Two</title></head><body><h1>Chapter Two</h1><p>Second chapter text.</p></body></html>'''
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/content.opf", package)
        z.writestr("OEBPS/nav.xhtml", nav)
        z.writestr("OEBPS/chapter1.xhtml", c1)
        z.writestr("OEBPS/chapter2.xhtml", c2)


def request_json(base: str, path: str, *, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


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
    checks = []

    def check(name, condition, detail=""):
        checks.append({"id": name, "ok": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    check("version_2b_3", module.APP_VERSION == "2B.3", module.APP_VERSION)
    check("speech_synthesis_local_only", "localService===true" in html and "confirmedLocalVoices" in html)
    check("online_only_voice_excluded_message", "will not use an online-only voice" in html)
    check("title_page_read_aloud", 'data-detail-action="read-aloud"' in html)
    for token in ("narrationPlay", "narrationPause", "narrationResume", "narrationStop", "narrationPreviousParagraph", "narrationNextParagraph", "narrationRestartChapter", "narrationReadFromHere", "narrationRememberPosition", "narrationTestVoice"):
        check(f"control_{token}", f'id="{token}"' in html)
    check("paragraph_and_boundary_highlighting", "kayock-narration-active" in html and "highlightNarrationBoundary" in html)
    check("keyboard_passage_selection", "event.key==='Enter'||event.key===' '" in html)
    check("auto_advance_off_by_default", 'id="narrationAutoAdvance" type="checkbox"' in html)
    check("ordinary_and_narration_positions_separate", "narrationIsDrivingScroll" in html and "Remember This Position" in html and "loadReaderChapter(activeReader.chapterIndex+1,0,'',true)" in html)
    check("bounded_speech_units", "splitNarrationText(value,maxLength=620)" in html)
    check("meaningful_elements_selected", "h1,h2,h3,h4,h5,h6,p,li,figcaption,hr,img[alt]" in html)
    check("hidden_and_page_furniture_ignored", "nav,header,footer,aside,[hidden]" in html)
    check("decorative_alt_filter", "usefulImageDescription" in html and "decorative|ornament|spacer" in html)
    check("interface_only_test_phrase", "Kayock’s Study local voice test. Read, research, preserve, discover." in html)
    check("no_cloud_tts_library", all(x not in source for x in ("edge_tts", "pyttsx3", "sapi.SpVoice", "api.openai.com/v1/audio")))
    check("pdf_read_aloud_not_enabled", "Read This to Me · EPUB only" in html)
    check("narration_sidecar_table", "CREATE TABLE IF NOT EXISTS epub_narration_state" in source)
    check("narration_api", 'parsed.path == "/api/epub/narration/state"' in source)

    tree = ast.parse(source)
    extracted = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "HTML" for t in node.targets):
            extracted = ast.literal_eval(node.value)
            break
    check("html_extractable", extracted == html)

    # Deterministic JavaScript helper test using mocked local and online voices.
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    def fn(name, next_name):
        start = script.index(f"function {name}")
        end = script.index(f"function {next_name}", start)
        return script[start:end]
    node_code = fn("confirmedLocalVoices", "splitNarrationText") + fn("splitNarrationText", "usefulImageDescription") + r'''
const voices=[
 {name:'Local One',lang:'en-US',localService:true},
 {name:'Cloud One',lang:'en-US',localService:false},
 {name:'Unknown One',lang:'en-US'}
];
const local=confirmedLocalVoices(voices);
if(local.length!==1||local[0].name!=='Local One')throw new Error('online voice filtering failed');
const chunks=splitNarrationText('One sentence. '.repeat(120),120);
if(chunks.length<2||chunks.some(x=>x.text.length>120))throw new Error('bounded chunking failed');
console.log(JSON.stringify({local:local.length,chunks:chunks.length}));
'''
    node_file = Path(tempfile.mkdtemp()) / "voice_logic.js"
    node_file.write_text(node_code, encoding="utf-8")
    node = subprocess.run(["node", str(node_file)], capture_output=True, text=True, timeout=60)
    check("mocked_voice_filter_and_chunking", node.returncode == 0, node.stderr or node.stdout)

    temp = Path(tempfile.mkdtemp(prefix="kayocks_v2b3_"))
    server = None
    try:
        paths = module.AppPaths(
            root=temp, library=temp/"Library", data=temp/"Data",
            database=temp/"Data"/"bibliotheca.sqlite3", log=temp/"Logs"/"bibliotheca.log",
            reports=temp/"Reports", epub_database=temp/"Data"/"epub_catalog.sqlite3",
            epub_cache=temp/"Data"/"EPUB_Covers", library_state_database=temp/"Data"/"study_library_state.sqlite3",
        )
        paths.library.mkdir(parents=True); paths.data.mkdir(parents=True)
        epub = paths.library / "Fiction" / "Star Trek" / "Narration Fixture.epub"
        make_epub(epub)
        original_hash = sha256(epub)
        indexed = module.index_library(paths)
        check("fixture_indexed", indexed.get("epubs_ready") == 1, indexed)
        item = module.list_ebooks(paths, status="ready")[0]
        identity = module.epub_reader_identity(paths, item["id"])
        reader_before = module.epub_reader_state(paths, identity)
        state = module.save_epub_narration_state(paths, identity, {
            "preferences": {"voice_name":"Local One","voice_lang":"en-US","rate":1.25,"pitch":0.9,"volume":0.8,"auto_advance":True},
            "paragraph_index": 4,
        })
        check("narration_preferences_persist", state["preferences"]["voice_name"] == "Local One" and state["preferences"]["rate"] == 1.25 and state["preferences"]["auto_advance"] is True, state)
        check("narration_paragraph_persists", state["paragraph_index"] == 4, state)
        check("reader_position_unchanged_by_narration", module.epub_reader_state(paths, identity) == reader_before)
        check("original_epub_unchanged", sha256(epub) == original_hash)
        main = module.connect_db(paths); main_tables={r[0] for r in main.execute("select name from sqlite_master where type='table'")}; main.close()
        cat = module.connect_epub_db(paths); cat_tables={r[0] for r in cat.execute("select name from sqlite_master where type='table'")}; cat.close()
        side = module.connect_library_state_db(paths); side_tables={r[0] for r in side.execute("select name from sqlite_master where type='table'")}; side.close()
        check("narration_not_in_pdf_or_epub_databases", "epub_narration_state" not in main_tables and "epub_narration_state" not in cat_tables)
        check("narration_only_in_state_sidecar", "epub_narration_state" in side_tables)

        server = module.StudyServer(("127.0.0.1",0), module.StudyHandler, paths)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval":0.05}, daemon=True); thread.start()
        base=f"http://127.0.0.1:{server.server_address[1]}"
        status, reader = request_json(base, f"/api/epub/reader?id={item['id']}")
        check("reader_api_includes_narration_state", status == 200 and reader["narration_state"]["paragraph_index"] == 4, reader)
        status, saved = request_json(base, "/api/epub/narration/state", method="POST", payload={"id":item["id"],"preferences":{"voice_name":"Local Two","voice_lang":"en-GB","rate":9,"pitch":-1,"volume":5,"auto_advance":False},"paragraph_index":2})
        prefs=saved.get("narration_state",{}).get("preferences",{})
        check("live_narration_api_clamps_values", status == 200 and prefs.get("rate") == 2.0 and prefs.get("pitch") == 0.5 and prefs.get("volume") == 1.0, saved)
        status, docs = request_json(base, "/api/documents?include_review=0")
        check("existing_pdf_api_unchanged", status == 200 and "documents" in docs, docs)
    finally:
        if server:
            server.shutdown(); server.server_close()

    result={"ok":all(c["ok"] for c in checks),"result":"verified","check_count":len(checks),"checks":checks,"interactive_audio_note":"Actual audio output and installed Windows voice quality require Eric's final interactive browser test.","external_network_used":False,"original_files_modified":0}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
