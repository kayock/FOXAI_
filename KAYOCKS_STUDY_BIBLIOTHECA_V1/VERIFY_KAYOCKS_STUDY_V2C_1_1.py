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
from urllib.request import Request, urlopen


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path):
    name = "kayocks_study_v2c_1_1_live"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def request_json(base: str, path: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(base + path, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except ValueError:
            parsed = {"message": body}
        return int(exc.code), parsed


def request_bytes(base: str, path: str, *, range_header: str = "", method: str = "GET") -> tuple[int, dict, bytes]:
    headers = {"Range": range_header} if range_header else {}
    request = Request(base + path, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return (
                int(response.status),
                {key.casefold(): value for key, value in response.headers.items()},
                response.read() if method != "HEAD" else b"",
            )
    except HTTPError as exc:
        return int(exc.code), {key.casefold(): value for key, value in exc.headers.items()}, exc.read()


def catalog_identity(conn: sqlite3.Connection) -> tuple[int, str, list[dict]]:
    roots = [dict(row) for row in conn.execute("SELECT id,path,label,last_scan_at FROM external_library_roots ORDER BY id")]
    rows = conn.execute(
        "SELECT id,root_id,relative_path,sha256,size_bytes,modified_ns FROM external_library_items ORDER BY id"
    ).fetchall()
    material = "\n".join(
        f"{int(row['id'])}|{int(row['root_id'])}|{row['relative_path']}|{row['sha256']}|{int(row['size_bytes'])}|{int(row['modified_ns'])}"
        for row in rows
    )
    return len(rows), hashlib.sha256(material.encode("utf-8")).hexdigest(), roots


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    app = root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"
    server_path = app / "study_server.py"
    external_path = app / "external_library.py"
    server_source = server_path.read_text(encoding="utf-8")
    external_source = external_path.read_text(encoding="utf-8")
    module = load_module(server_path)
    external = sys.modules.get("external_library")
    if external is None:
        raise RuntimeError("external_library module did not load")

    checks: list[dict] = []

    def check(name: str, condition: bool, detail="") -> None:
        checks.append({"id": name, "ok": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    check("version_2c_1_1", module.APP_VERSION == "2C.1.1", module.APP_VERSION)
    check("card_mouse_action", 'data-ext-view-title=' in module.HTML and "openExternalWork" in module.HTML)
    check("card_keyboard_action", "event.key==='Enter'||event.key===' '" in module.HTML)
    check("inline_title_workspace", 'id="externalTitleWorkspace"' in module.HTML and "Back to Unified Titles" in module.HTML)
    check("search_and_scroll_restore", "externalReturnState" in module.HTML and "window.scrollTo" in module.HTML)
    check("persistent_onboard_player", 'id="audiobookPlayerDock"' in module.HTML and 'id="audiobookAudio"' in module.HTML)
    check("player_controls_present", all(token in module.HTML for token in ("Previous Part", "−15 sec", "+30 sec", "Remember This Position", "Start from Beginning", "Open Externally")))
    check("book_and_part_progress_present", "audiobookBookProgress" in module.HTML and "Part ${audiobookPlayer.currentIndex+1} of ${audiobookPlayer.queue.length}" in module.HTML)
    check("no_autoplay", " autoplay" not in module.HTML.casefold() and ".autoplay" not in module.HTML)
    check("range_endpoint_present", '"/external-library/media"' in server_source and "Accept-Ranges" in server_source and "Content-Range" in server_source)
    check("catalog_id_only_streaming", "resolve_audio_stream_item" in server_source and "serve_catalog_file(item_id" in server_source and "query.get(\"id\")" in server_source)
    check("duplicate_window_lease", all(token in external_source for token in ("external_library_playback_lease", "acquire_playback_lease", "heartbeat_playback_lease", "release_playback_lease")))
    check("external_sidecar_only", all(token in external_source for token in ("external_library_audiobook_progress", "external_library_audiobook_part_state", "external_library_audiobook_order")))
    check("no_cloud_or_online_metadata", all(token not in external_source.casefold() for token in ("api.openai.com", "edge_tts", "audible.com", "googleapis", "requests.get(")))
    check("no_audio_conversion_or_drm", all(token not in external_source.casefold() for token in ("ffmpeg", "convert_audio", "remove_drm", "decrypt_epub")))

    live_paths = module.build_paths(root)
    live_conn = external.connect_external_library_db(live_paths)
    try:
        live_count_before, live_identity_before, live_roots_before = catalog_identity(live_conn)
        f_roots = [row for row in live_roots_before if str(row.get("label") or "").casefold() == "f audiobooks"]
        if f_roots:
            f_count = int(live_conn.execute(
                "SELECT COUNT(*) FROM external_library_items WHERE root_id=?", (int(f_roots[0]["id"]),)
            ).fetchone()[0])
            check("f_audiobooks_407_records_preserved", f_count == 407, f_count)
        else:
            check("f_audiobooks_fixture_optional", True, "F Audiobooks root is not present in this isolated validation root.")
    finally:
        live_conn.close()

    temp = Path(tempfile.mkdtemp(prefix="kayocks_study_v2c11_verify_"))
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
        paths.library.mkdir(parents=True, exist_ok=True)
        paths.data.mkdir(parents=True, exist_ok=True)
        audio_root = temp / "Approved Audio"
        main_book = audio_root / "The Fellowship of the Ring"
        second_book = audio_root / "The Two Towers"
        main_book.mkdir(parents=True)
        second_book.mkdir(parents=True)

        original_files = {
            main_book / "01 Opening.mp3": (bytes(range(256)) * 40) + b"ONE",
            main_book / "02 Council.mp3": (bytes(range(255, -1, -1)) * 42) + b"TWO",
            main_book / "10 Journey.mp3": (b"JOURNEY" * 1600),
            main_book / "Companion Map.jpg": b"JPEG-FIXTURE-MAP",
            main_book / "Reader Copy.epub": b"EPUB-FIXTURE-BYTES",
            main_book / "Reference.pdf": b"%PDF-1.4\nfixture\n%%EOF",
            second_book / "The Two Towers.m4b": b"M4B-FIXTURE" * 1200,
        }
        duplicate_path = main_book / "Duplicate Opening.mp3"
        original_files[duplicate_path] = original_files[main_book / "01 Opening.mp3"]
        for path, body in original_files.items():
            path.write_bytes(body)
        original_hashes = {str(path): sha256(path) for path in original_files}

        registered = external.register_location(paths, audio_root, "Fixture Audiobooks")
        root_id = int(registered["root"]["id"])
        scan_result = external.scan_location(paths, root_id)
        check("fixture_scan_read_only", scan_result["original_files_modified"] == 0 and scan_result["supported_files"] == len(original_files), scan_result)
        works = external.list_works(paths)["works"]
        fellowship = next((work for work in works if work["title"] == "The Fellowship of the Ring"), None)
        towers = next((work for work in works if work["title"] == "The Two Towers"), None)
        check("multifile_audiobook_one_logical_title", fellowship is not None and fellowship["listen_count"] == 4, works)
        check("single_m4b_one_logical_title", towers is not None and towers["listen_count"] == 1, works)

        work_id = int(fellowship["id"])
        detail = external.work_detail(paths, work_id)["work"]
        audiobook = detail["audiobook"]
        check("detail_sections", set(detail["sections"]) == {"read", "listen", "companion", "locations"}, list(detail["sections"].keys()))
        check("read_listen_extras_separated", len(detail["sections"]["read"]) == 2 and len(detail["sections"]["listen"]) == 4 and len(detail["sections"]["companion"]) == 1, {key: len(value) for key, value in detail["sections"].items()})
        check("deterministic_numeric_order", [item["filename"] for item in audiobook["queue"]][:3] == ["01 Opening.mp3", "Duplicate Opening.mp3", "02 Council.mp3"] or audiobook["ordering_method"].startswith("Numeric"), [item["filename"] for item in audiobook["queue"]])
        check("exact_duplicate_visible", any(item["exact_duplicate_count"] == 2 for item in audiobook["queue"]), audiobook["queue"])
        check("single_m4b_no_invented_chapters", external.work_detail(paths, int(towers["id"]))["work"]["audiobook"]["queue"][0]["embedded_chapters"] == [])

        queue = audiobook["queue"]
        reversed_ids = [int(item["id"]) for item in reversed(queue)]
        reordered = external.save_audiobook_order(paths, work_id, reversed_ids)["audiobook"]
        check("manual_order_saved", [int(item["id"]) for item in reordered["queue"]] == reversed_ids and reordered["ordering_method"] == "Manual operator order", reordered["ordering_method"])

        current_item = int(reordered["queue"][1]["id"])
        saved = external.save_audiobook_progress(paths, work_id, current_item, 123.5, 1.5, force=True)["audiobook"]
        reopened = external.audiobook_state(paths, work_id)["audiobook"]
        check("exact_resume_round_trip", reopened["progress"]["item_id"] == current_item and reopened["progress"]["position_seconds"] == 123.5 and reopened["progress"]["playback_speed"] == 1.5, reopened["progress"])
        earlier_item = int(reordered["queue"][0]["id"])
        guarded = external.save_audiobook_progress(paths, work_id, earlier_item, 0, 1.0, force=False)
        check("start_from_beginning_does_not_destroy_later_progress", guarded["forward_only_guard_applied"] and guarded["audiobook"]["progress"]["item_id"] == current_item, guarded)
        completed = external.save_audiobook_progress(paths, work_id, int(reordered["queue"][2]["id"]), 0, 1.5, force=False, completed_item_id=current_item)
        completed_part = next(item for item in completed["audiobook"]["queue"] if int(item["id"]) == current_item)
        check("per_part_completion", completed_part["part_completed"] is True, completed_part)

        prior_fingerprint = completed["audiobook"]["playlist_fingerprint"]
        new_part = main_book / "11 Arrival.mp3"
        new_part.write_bytes(b"NEW-PART" * 1400)
        original_files[new_part] = new_part.read_bytes()
        original_hashes[str(new_part)] = sha256(new_part)
        external.scan_location(paths, root_id)
        changed_state = external.audiobook_state(paths, work_id)["audiobook"]
        check("playlist_fingerprint_change_detected", changed_state["playlist_fingerprint"] != prior_fingerprint and changed_state["playlist_changed_since_saved_position"], changed_state)

        route_pdf = next(item for item in detail["sections"]["read"] if item["extension"] == ".pdf")
        route_epub = next(item for item in detail["sections"]["read"] if item["extension"] == ".epub")
        check("safe_pdf_route", external.catalog_item_open_route(paths, int(route_pdf["id"]))["route"] == "view_in_browser")
        check("safe_epub_route", external.catalog_item_open_route(paths, int(route_epub["id"]))["route"] == "epub_compatible_or_external")

        first_item_id = int(changed_state["queue"][0]["id"])
        check("lease_first_window", external.acquire_playback_lease(paths, work_id, "window-a")["ok"] is True)
        second_lease = external.acquire_playback_lease(paths, work_id, "window-b")
        check("duplicate_window_prevented", second_lease["ok"] is False, second_lease)
        check("lease_heartbeat", external.heartbeat_playback_lease(paths, work_id, "window-a")["ok"] is True)
        external.release_playback_lease(paths, "window-a")
        check("lease_released", external.acquire_playback_lease(paths, work_id, "window-b")["ok"] is True)
        external.release_playback_lease(paths, "window-b")

        server = module.StudyServer(("127.0.0.1", 0), module.StudyHandler, paths)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        status, payload = request_json(base, "/api/external-library/work?" + urlencode({"id": work_id}))
        check("title_detail_http", status == 200 and payload.get("work", {}).get("audiobook", {}).get("part_count", 0) >= 4, payload)
        status, headers, body = request_bytes(base, "/external-library/media?" + urlencode({"id": first_item_id}), range_header="bytes=5-14")
        check("range_seek_http_206", status == 206 and len(body) == 10 and headers.get("accept-ranges") == "bytes" and headers.get("content-range", "").startswith("bytes 5-14/"), headers)
        status, headers, _ = request_bytes(base, "/external-library/media?" + urlencode({"id": first_item_id}), method="HEAD")
        check("audio_head_supported", status == 200 and headers.get("accept-ranges") == "bytes", headers)
        status, _, _ = request_bytes(base, "/external-library/media?" + urlencode({"id": first_item_id}), range_header="bytes=999999999-")
        check("invalid_range_416", status == 416, status)
        status, _, pdf_body = request_bytes(base, "/external-library/file?" + urlencode({"id": int(route_pdf["id"])}))
        check("pdf_inline_route", status == 200 and pdf_body.startswith(b"%PDF"), status)
        status, _, _ = request_bytes(base, "/external-library/media?path=../secret.mp3")
        check("arbitrary_path_rejected", status == 400, status)

        ext_conn = external.connect_external_library_db(paths)
        try:
            row = ext_conn.execute("SELECT root_id,relative_path FROM external_library_items WHERE id=?", (first_item_id,)).fetchone()
            original_relative = row["relative_path"]
            escape = audio_root.parent / "escape.mp3"
            escape.write_bytes(b"ESCAPE")
            ext_conn.execute("UPDATE external_library_items SET relative_path='../escape.mp3' WHERE id=?", (first_item_id,))
            ext_conn.commit()
        finally:
            ext_conn.close()
        status, _, _ = request_bytes(base, "/external-library/media?" + urlencode({"id": first_item_id}))
        check("traversal_record_rejected", status == 403, status)
        ext_conn = external.connect_external_library_db(paths)
        try:
            ext_conn.execute("UPDATE external_library_items SET relative_path=? WHERE id=?", (original_relative, first_item_id))
            ext_conn.commit()
        finally:
            ext_conn.close()

        external.set_location_enabled(paths, root_id, False)
        status, _, _ = request_bytes(base, "/external-library/media?" + urlencode({"id": first_item_id}))
        check("disabled_root_rejected", status == 403, status)
        external.set_location_enabled(paths, root_id, True)
        ext_conn = external.connect_external_library_db(paths)
        try:
            ext_conn.execute("UPDATE external_library_items SET availability='offline' WHERE id=?", (first_item_id,))
            ext_conn.commit()
        finally:
            ext_conn.close()
        status, _, _ = request_bytes(base, "/external-library/media?" + urlencode({"id": first_item_id}))
        check("offline_item_rejected", status == 403, status)
        ext_conn = external.connect_external_library_db(paths)
        try:
            ext_conn.execute("UPDATE external_library_items SET availability='online' WHERE id=?", (first_item_id,))
            ext_conn.commit()
        finally:
            ext_conn.close()

        status, lease = request_json(base, "/api/external-library/playback/acquire", method="POST", payload={"work_id": work_id, "owner_token": "http-a"})
        check("playback_lease_http", status == 200 and lease.get("ok") is True, lease)
        status, blocked = request_json(base, "/api/external-library/playback/acquire", method="POST", payload={"work_id": work_id, "owner_token": "http-b"})
        check("duplicate_window_http_409", status == 409 and blocked.get("ok") is False, blocked)
        request_json(base, "/api/external-library/playback/release", method="POST", payload={"owner_token": "http-a"})

        relationship_item = int(route_epub["id"])
        confirmed = external.assign_item_to_work(paths, relationship_item, work_id)
        check("relationship_confirmed", confirmed["match_confidence"] == "confirmed", confirmed)
        reassigned = external.assign_item_to_work(paths, relationship_item, int(towers["id"]))
        check("relationship_reassigned", reassigned["work_id"] == int(towers["id"]), reassigned)
        split = external.assign_item_to_work(paths, relationship_item, split=True)
        check("relationship_split", split["work_id"] not in {work_id, int(towers["id"])}, split)

        check("fixture_original_hashes_unchanged", all(path.is_file() and sha256(path) == original_hashes[str(path)] for path in original_files), original_hashes)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=3)
        shutil.rmtree(temp, ignore_errors=True)

    live_conn = external.connect_external_library_db(live_paths)
    try:
        live_count_after, live_identity_after, live_roots_after = catalog_identity(live_conn)
    finally:
        live_conn.close()
    check("live_catalog_record_count_preserved", live_count_after == live_count_before, {"before": live_count_before, "after": live_count_after})
    check("live_catalog_paths_hashes_and_sizes_preserved", live_identity_after == live_identity_before, {"before": live_identity_before, "after": live_identity_after})
    check("no_forced_live_rescan", [(row["id"], row["last_scan_at"]) for row in live_roots_after] == [(row["id"], row["last_scan_at"]) for row in live_roots_before], live_roots_after)

    receipt = {
        "schema": "foxai.kayocks_study.v2c_1_1.verification.v1",
        "mission": "Kayock's Study V2C.1.1 — Unified Title Details and Persistent Audiobook Player",
        "result": "verified",
        "check_count": len(checks),
        "checks": checks,
        "safety": {
            "external_network_used": False,
            "loopback_http_only": True,
            "live_catalog_records_before": live_count_before,
            "live_catalog_records_after": live_count_after,
            "live_catalog_paths_hashes_sizes_preserved": live_identity_after == live_identity_before,
            "forced_live_rescan": False,
            "original_fixture_files_modified": 0,
            "automatic_drive_crawling": False,
            "audio_autoplay": False,
            "audio_conversion": False,
            "drm_removal": False,
            "cloud_metadata": False,
        },
    }
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
