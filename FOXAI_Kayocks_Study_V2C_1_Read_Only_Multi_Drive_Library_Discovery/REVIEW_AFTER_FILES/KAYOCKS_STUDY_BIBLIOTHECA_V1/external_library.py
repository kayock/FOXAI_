from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import struct
import subprocess
import sys
from threading import RLock, Thread
import time
import wave
import xml.etree.ElementTree as ET
import zipfile

SUPPORTED_EXTENSIONS = {
    ".epub", ".pdf", ".mobi", ".azw", ".azw3",
    ".m4b", ".mp3", ".flac", ".ogg", ".wav",
    ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp",
}
READ_EXTENSIONS = {".epub", ".pdf", ".mobi", ".azw", ".azw3"}
LISTEN_EXTENSIONS = {".m4b", ".mp3", ".flac", ".ogg", ".wav"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
MAX_PREVIEW_FILES = 500_000
MAX_METADATA_BYTES = 8 * 1024 * 1024
_HASH_BLOCK = 4 * 1024 * 1024
_TOKEN = re.compile(r"[a-z0-9]+")
_PART_MARKERS = re.compile(
    r"(?:\b(?:part|chapter|disc|disk|cd|track|book)\s*\d+\b|\b\d{1,3}\s*of\s*\d{1,3}\b)",
    re.IGNORECASE,
)
_FORMAT_MARKERS = re.compile(
    r"\b(?:unabridged|abridged|audiobook|audio book|retail|epub|mobi|azw3?|pdf|mp3|m4b|flac|ogg|wav)\b",
    re.IGNORECASE,
)
_BRACKETED = re.compile(r"\[[^\]]{0,120}\]|\([^)]{0,120}\)")


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def database_path(paths) -> Path:
    return Path(paths.data) / "external_library.sqlite3"


def connect_external_library_db(paths) -> sqlite3.Connection:
    path = database_path(paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS external_library_roots(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            label TEXT NOT NULL DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            availability TEXT NOT NULL DEFAULT 'unknown',
            drive_identity TEXT NOT NULL DEFAULT '',
            preview_json TEXT NOT NULL DEFAULT '{}',
            last_scan_at TEXT NOT NULL DEFAULT '',
            last_error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS external_library_works(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_title TEXT NOT NULL,
            normalized_author TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            author TEXT NOT NULL DEFAULT '',
            series TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_external_works_title
            ON external_library_works(normalized_title, normalized_author);
        CREATE TABLE IF NOT EXISTS external_library_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            root_id INTEGER NOT NULL REFERENCES external_library_roots(id) ON DELETE CASCADE,
            work_id INTEGER REFERENCES external_library_works(id) ON DELETE SET NULL,
            relative_path TEXT NOT NULL,
            filename TEXT NOT NULL,
            extension TEXT NOT NULL,
            media_kind TEXT NOT NULL,
            role TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            modified_ns INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            title TEXT NOT NULL,
            normalized_title TEXT NOT NULL,
            author TEXT NOT NULL DEFAULT '',
            normalized_author TEXT NOT NULL DEFAULT '',
            series TEXT NOT NULL DEFAULT '',
            volume TEXT NOT NULL DEFAULT '',
            narrator TEXT NOT NULL DEFAULT '',
            duration_seconds REAL,
            identifier TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            availability TEXT NOT NULL DEFAULT 'online',
            match_confidence TEXT NOT NULL DEFAULT 'needs_review',
            match_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(root_id, relative_path)
        );
        CREATE INDEX IF NOT EXISTS idx_external_items_sha
            ON external_library_items(sha256);
        CREATE INDEX IF NOT EXISTS idx_external_items_work
            ON external_library_items(work_id, role);
        CREATE INDEX IF NOT EXISTS idx_external_items_title
            ON external_library_items(normalized_title, normalized_author);
        CREATE TABLE IF NOT EXISTS external_library_manual_links(
            item_id INTEGER PRIMARY KEY REFERENCES external_library_items(id) ON DELETE CASCADE,
            work_id INTEGER NOT NULL REFERENCES external_library_works(id) ON DELETE CASCADE,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    return conn


def normalize_text(value: object, limit: int = 500) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def clean_title(value: str) -> str:
    text = normalize_text(value, 500)
    text = Path(text).stem if "." in Path(text).name else text
    text = text.replace("_", " ").replace(".", " ")
    text = _BRACKETED.sub(" ", text)
    text = _PART_MARKERS.sub(" ", text)
    text = _FORMAT_MARKERS.sub(" ", text)
    text = re.sub(r"\s+-\s+(?:read by|narrated by)\s+.+$", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" -–—_.")
    return text[:500] or "Untitled"


def normalized_key(value: str) -> str:
    return " ".join(_TOKEN.findall(clean_title(value).casefold()))


def normalized_person(value: str) -> str:
    return " ".join(_TOKEN.findall(normalize_text(value).casefold()))


def drive_identity(path: Path) -> str:
    anchor = path.anchor or str(path)
    try:
        stat = path.stat()
        return f"{anchor}|dev={getattr(stat, 'st_dev', 0)}"
    except OSError:
        return anchor


def _safe_registered_path(raw: object, *, must_exist: bool = True) -> Path:
    text = str(raw or "").strip().strip('"')
    if not text:
        raise ValueError("Enter an exact library folder path.")
    candidate = Path(text).expanduser()
    try:
        resolved = candidate.resolve(strict=must_exist)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"The library folder is unavailable: {exc}") from exc
    if must_exist and not resolved.is_dir():
        raise ValueError("The approved library location must be a folder.")
    if resolved.parent == resolved:
        raise ValueError("Register a specific library folder, not an entire drive root.")
    return resolved


def _is_safe_child(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def iter_supported_files(root: Path):
    stack = [root]
    seen = 0
    while stack:
        folder = stack.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    seen += 1
                    if seen > MAX_PREVIEW_FILES:
                        raise RuntimeError(
                            f"This preview exceeded the safety limit of {MAX_PREVIEW_FILES:,} entries. Register a narrower folder."
                        )
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue
                    except OSError:
                        continue
                    path = Path(entry.path)
                    if path.suffix.casefold() in SUPPORTED_EXTENSIONS and _is_safe_child(root, path):
                        yield path
        except PermissionError:
            continue
        except FileNotFoundError:
            continue


def preview_location(raw_path: object) -> dict:
    root = _safe_registered_path(raw_path, must_exist=True)
    counts: dict[str, int] = {}
    total_bytes = 0
    supported_files = 0
    access_errors = 0
    started = time.time()
    try:
        for path in iter_supported_files(root):
            try:
                size = path.stat().st_size
            except OSError:
                access_errors += 1
                continue
            ext = path.suffix.casefold()
            counts[ext] = counts.get(ext, 0) + 1
            supported_files += 1
            total_bytes += int(size)
    except RuntimeError:
        raise
    return {
        "ok": True,
        "path": str(root),
        "label_suggestion": root.name,
        "availability": "online",
        "drive_identity": drive_identity(root),
        "supported_files": supported_files,
        "counts_by_extension": dict(sorted(counts.items())),
        "total_bytes": total_bytes,
        "estimated_hash_bytes": total_bytes,
        "access_errors": access_errors,
        "elapsed_seconds": round(time.time() - started, 3),
        "read_only": True,
        "files_modified": 0,
        "message": (
            f"Preview found {supported_files:,} supported files. "
            "No hashes were calculated and no files were changed."
        ),
    }


def register_location(paths, raw_path: object, label: object = "") -> dict:
    preview = preview_location(raw_path)
    now = iso_now()
    clean_label = normalize_text(label, 160) or preview["label_suggestion"]
    conn = connect_external_library_db(paths)
    try:
        conn.execute(
            """
            INSERT INTO external_library_roots(
                path,label,enabled,availability,drive_identity,preview_json,
                last_scan_at,last_error,created_at,updated_at
            ) VALUES(?,?,?,?,?,?, '', '', ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                label=excluded.label,
                enabled=1,
                availability=excluded.availability,
                drive_identity=excluded.drive_identity,
                preview_json=excluded.preview_json,
                last_error='',
                updated_at=excluded.updated_at
            """,
            (
                preview["path"], clean_label, 1, "online",
                preview["drive_identity"], json.dumps(preview, ensure_ascii=False),
                now, now,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM external_library_roots WHERE path=?", (preview["path"],)
        ).fetchone()
        return {"ok": True, "root": public_root(conn, row), "preview": preview}
    finally:
        conn.close()


def _root_availability(path_text: str) -> str:
    try:
        return "online" if Path(path_text).is_dir() else "offline"
    except OSError:
        return "offline"


def public_root(conn: sqlite3.Connection, row: sqlite3.Row | dict) -> dict:
    item = dict(row)
    availability = _root_availability(item["path"])
    if availability != item.get("availability"):
        conn.execute(
            "UPDATE external_library_roots SET availability=?,updated_at=? WHERE id=?",
            (availability, iso_now(), item["id"]),
        )
        conn.execute(
            "UPDATE external_library_items SET availability=? WHERE root_id=?",
            (availability, item["id"]),
        )
        conn.commit()
        item["availability"] = availability
    counts = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(size_bytes),0) AS bytes FROM external_library_items WHERE root_id=?",
        (item["id"],),
    ).fetchone()
    roles = {
        r["role"]: r["n"]
        for r in conn.execute(
            "SELECT role,COUNT(*) AS n FROM external_library_items WHERE root_id=? GROUP BY role",
            (item["id"],),
        ).fetchall()
    }
    try:
        preview = json.loads(item.get("preview_json") or "{}")
    except json.JSONDecodeError:
        preview = {}
    return {
        "id": int(item["id"]),
        "path": item["path"],
        "label": item["label"],
        "enabled": bool(item["enabled"]),
        "availability": item["availability"],
        "drive_identity": item["drive_identity"],
        "last_scan_at": item["last_scan_at"],
        "last_error": item["last_error"],
        "catalog_files": int(counts["n"]),
        "catalog_bytes": int(counts["bytes"]),
        "roles": roles,
        "preview": preview,
    }


def list_locations(paths) -> dict:
    conn = connect_external_library_db(paths)
    try:
        rows = conn.execute(
            "SELECT * FROM external_library_roots ORDER BY label COLLATE NOCASE,path COLLATE NOCASE"
        ).fetchall()
        roots = [public_root(conn, row) for row in rows]
        return {
            "ok": True,
            "roots": roots,
            "automatic_drive_crawling": False,
            "registered_root_count": len(roots),
        }
    finally:
        conn.close()


def set_location_enabled(paths, root_id: int, enabled: bool) -> dict:
    conn = connect_external_library_db(paths)
    try:
        row = conn.execute("SELECT * FROM external_library_roots WHERE id=?", (root_id,)).fetchone()
        if not row:
            raise ValueError("Library location not found.")
        conn.execute(
            "UPDATE external_library_roots SET enabled=?,updated_at=? WHERE id=?",
            (1 if enabled else 0, iso_now(), root_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM external_library_roots WHERE id=?", (root_id,)).fetchone()
        return {"ok": True, "root": public_root(conn, row)}
    finally:
        conn.close()


def remove_location_from_catalog(paths, root_id: int) -> dict:
    if EXTERNAL_LIBRARY_STATE.snapshot().get("running") and EXTERNAL_LIBRARY_STATE.snapshot().get("root_id") == root_id:
        raise RuntimeError("Wait for the current library-location scan to finish before removing this root.")
    conn = connect_external_library_db(paths)
    try:
        row = conn.execute("SELECT path,label FROM external_library_roots WHERE id=?", (root_id,)).fetchone()
        if not row:
            raise ValueError("Library location not found.")
        count = conn.execute(
            "SELECT COUNT(*) FROM external_library_items WHERE root_id=?", (root_id,)
        ).fetchone()[0]
        conn.execute("DELETE FROM external_library_roots WHERE id=?", (root_id,))
        _remove_orphan_works(conn)
        conn.commit()
        return {
            "ok": True,
            "removed_catalog_items": int(count),
            "original_files_modified": 0,
            "path": row["path"],
            "message": "The location was removed from the catalog only. Original files were untouched.",
        }
    finally:
        conn.close()


def _remove_orphan_works(conn: sqlite3.Connection) -> None:
    conn.execute(
        "DELETE FROM external_library_works WHERE id NOT IN (SELECT DISTINCT work_id FROM external_library_items WHERE work_id IS NOT NULL)"
    )


def file_sha256(path: Path, progress=None) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_HASH_BLOCK), b""):
            digest.update(block)
            if progress:
                progress(len(block))
    return digest.hexdigest()


def _xml_local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _epub_metadata(path: Path) -> dict:
    result: dict = {}
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if "META-INF/encryption.xml" in names:
            result["protected"] = True
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next(
            (node.attrib.get("full-path") for node in container.iter() if _xml_local(node.tag) == "rootfile"),
            "",
        )
        if not rootfile:
            return result
        package = ET.fromstring(archive.read(rootfile))
        for node in package.iter():
            name = _xml_local(node.tag)
            value = normalize_text("".join(node.itertext()), 4000)
            if not value:
                continue
            if name == "title" and not result.get("title"):
                result["title"] = value
            elif name in {"creator", "author"} and not result.get("author"):
                result["author"] = value
            elif name == "identifier" and not result.get("identifier"):
                result["identifier"] = value
            elif name == "description" and not result.get("description"):
                result["description"] = value
            elif name == "publisher" and not result.get("publisher"):
                result["publisher"] = value
            elif name == "date" and not result.get("date"):
                result["date"] = value
        result["format"] = "EPUB"
    return result


def _pdf_metadata(path: Path) -> dict:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path), strict=False)
        raw = reader.metadata or {}
        return {
            "title": normalize_text(raw.get("/Title"), 500),
            "author": normalize_text(raw.get("/Author"), 300),
            "description": normalize_text(raw.get("/Subject"), 1500),
            "pages": len(reader.pages),
            "format": "PDF",
        }
    except Exception as exc:
        return {"metadata_error": f"{type(exc).__name__}: {exc}", "format": "PDF"}


def _synchsafe(value: bytes) -> int:
    total = 0
    for byte in value:
        total = (total << 7) | (byte & 0x7F)
    return total


def _decode_id3_text(data: bytes) -> str:
    if not data:
        return ""
    encoding = data[0]
    body = data[1:]
    codecs = {0: "latin-1", 1: "utf-16", 2: "utf-16-be", 3: "utf-8"}
    try:
        return normalize_text(body.decode(codecs.get(encoding, "latin-1"), errors="replace").strip("\x00"), 500)
    except Exception:
        return ""


def _mp3_metadata(path: Path) -> dict:
    result: dict = {"format": "MP3"}
    with path.open("rb") as handle:
        header = handle.read(10)
        if header[:3] == b"ID3" and len(header) == 10:
            version = header[3]
            tag_size = min(_synchsafe(header[6:10]), MAX_METADATA_BYTES)
            data = handle.read(tag_size)
            pos = 0
            frame_map = {"TIT2": "title", "TPE1": "author", "TALB": "series", "TRCK": "volume", "TPE2": "narrator"}
            while pos + 10 <= len(data):
                frame_id = data[pos:pos+4].decode("latin-1", errors="ignore")
                if not frame_id.strip("\x00"):
                    break
                raw_size = data[pos+4:pos+8]
                size = _synchsafe(raw_size) if version == 4 else int.from_bytes(raw_size, "big")
                if size <= 0 or pos + 10 + size > len(data):
                    break
                content = data[pos+10:pos+10+size]
                if frame_id in frame_map:
                    value = _decode_id3_text(content)
                    if value:
                        result[frame_map[frame_id]] = value
                pos += 10 + size
    return result


def _wav_metadata(path: Path) -> dict:
    result: dict = {"format": "WAV"}
    try:
        with wave.open(str(path), "rb") as audio:
            rate = audio.getframerate()
            frames = audio.getnframes()
            result["duration_seconds"] = round(frames / rate, 3) if rate else None
            result["channels"] = audio.getnchannels()
            result["sample_rate"] = rate
    except Exception as exc:
        result["metadata_error"] = f"{type(exc).__name__}: {exc}"
    return result


def _flac_metadata(path: Path) -> dict:
    result: dict = {"format": "FLAC"}
    with path.open("rb") as handle:
        if handle.read(4) != b"fLaC":
            return result
        last = False
        while not last:
            header = handle.read(4)
            if len(header) < 4:
                break
            last = bool(header[0] & 0x80)
            block_type = header[0] & 0x7F
            length = int.from_bytes(header[1:4], "big")
            if length > MAX_METADATA_BYTES:
                handle.seek(length, 1)
                continue
            data = handle.read(length)
            if block_type == 0 and len(data) >= 18:
                packed = int.from_bytes(data[10:18], "big")
                sample_rate = (packed >> 44) & 0xFFFFF
                total_samples = packed & ((1 << 36) - 1)
                if sample_rate:
                    result["duration_seconds"] = round(total_samples / sample_rate, 3)
            elif block_type == 4 and len(data) >= 8:
                pos = 0
                vendor_len = int.from_bytes(data[pos:pos+4], "little"); pos += 4 + vendor_len
                if pos + 4 <= len(data):
                    count = int.from_bytes(data[pos:pos+4], "little"); pos += 4
                    for _ in range(min(count, 1000)):
                        if pos + 4 > len(data): break
                        n = int.from_bytes(data[pos:pos+4], "little"); pos += 4
                        if pos + n > len(data): break
                        entry = data[pos:pos+n].decode("utf-8", errors="replace"); pos += n
                        if "=" in entry:
                            key, value = entry.split("=", 1)
                            key = key.casefold()
                            target = {"title":"title", "artist":"author", "album":"series", "tracknumber":"volume", "composer":"narrator"}.get(key)
                            if target and not result.get(target):
                                result[target] = normalize_text(value, 500)
    return result


def _ogg_metadata(path: Path) -> dict:
    result: dict = {"format": "OGG"}
    data = path.read_bytes()[:MAX_METADATA_BYTES]
    marker = data.find(b"\x03vorbis")
    if marker >= 0:
        pos = marker + 7
        if pos + 4 <= len(data):
            vendor_len = int.from_bytes(data[pos:pos+4], "little"); pos += 4 + vendor_len
            if pos + 4 <= len(data):
                count = int.from_bytes(data[pos:pos+4], "little"); pos += 4
                for _ in range(min(count, 1000)):
                    if pos + 4 > len(data): break
                    n = int.from_bytes(data[pos:pos+4], "little"); pos += 4
                    if pos + n > len(data): break
                    entry = data[pos:pos+n].decode("utf-8", errors="replace"); pos += n
                    if "=" in entry:
                        key, value = entry.split("=", 1)
                        target = {"title":"title", "artist":"author", "album":"series", "tracknumber":"volume"}.get(key.casefold())
                        if target and not result.get(target):
                            result[target] = normalize_text(value, 500)
    return result


def _m4b_duration(path: Path) -> dict:
    result: dict = {"format": "M4B"}
    try:
        with path.open("rb") as handle:
            data = handle.read(min(path.stat().st_size, MAX_METADATA_BYTES))
        pos = 0
        while True:
            idx = data.find(b"mvhd", pos)
            if idx < 0:
                break
            if idx + 24 <= len(data):
                version = data[idx+4]
                if version == 0 and idx + 24 <= len(data):
                    timescale = int.from_bytes(data[idx+16:idx+20], "big")
                    duration = int.from_bytes(data[idx+20:idx+24], "big")
                elif version == 1 and idx + 36 <= len(data):
                    timescale = int.from_bytes(data[idx+28:idx+32], "big")
                    duration = int.from_bytes(data[idx+32:idx+40], "big")
                else:
                    timescale = duration = 0
                if timescale:
                    result["duration_seconds"] = round(duration / timescale, 3)
                    break
            pos = idx + 4
    except Exception as exc:
        result["metadata_error"] = f"{type(exc).__name__}: {exc}"
    return result


def metadata_for_file(path: Path) -> dict:
    ext = path.suffix.casefold()
    try:
        if ext == ".epub": return _epub_metadata(path)
        if ext == ".pdf": return _pdf_metadata(path)
        if ext == ".mp3": return _mp3_metadata(path)
        if ext == ".wav": return _wav_metadata(path)
        if ext == ".flac": return _flac_metadata(path)
        if ext == ".ogg": return _ogg_metadata(path)
        if ext == ".m4b": return _m4b_duration(path)
        if ext in {".mobi", ".azw", ".azw3"}: return {"format": ext[1:].upper()}
        if ext in IMAGE_EXTENSIONS: return {"format": ext[1:].upper()}
    except Exception as exc:
        return {"metadata_error": f"{type(exc).__name__}: {exc}", "format": ext[1:].upper()}
    return {"format": ext[1:].upper()}


def role_for_path(path: Path) -> tuple[str, str]:
    ext = path.suffix.casefold()
    if ext in LISTEN_EXTENSIONS:
        return "listen", "audiobook"
    if ext in IMAGE_EXTENSIONS:
        name = path.stem.casefold()
        return "companion", "map" if any(token in name for token in ("map", "atlas", "diagram")) else "image"
    if ext in READ_EXTENSIONS:
        name = path.stem.casefold()
        if any(token in name for token in ("map", "atlas", "companion", "guide", "insert", "booklet")):
            return "companion", "document"
        return "read", "ebook_or_document"
    return "companion", "other"


def derive_title(path: Path, metadata: dict, role: str) -> str:
    title = normalize_text(metadata.get("title"), 500)
    if title:
        return clean_title(title)
    if role == "listen" and _PART_MARKERS.search(path.stem):
        return clean_title(path.parent.name)
    return clean_title(path.stem)


def _find_or_create_work(
    conn: sqlite3.Connection,
    *, title: str, author: str, normalized_title: str, normalized_author: str,
    series: str, sha256: str,
) -> tuple[int, str, str]:
    manual_or_duplicate = conn.execute(
        "SELECT work_id FROM external_library_items WHERE sha256=? AND work_id IS NOT NULL ORDER BY id LIMIT 1",
        (sha256,),
    ).fetchone()
    if manual_or_duplicate:
        return int(manual_or_duplicate["work_id"]), "confirmed", "Exact content hash matches an existing catalog item."
    rows = conn.execute(
        "SELECT * FROM external_library_works WHERE normalized_title=? ORDER BY id",
        (normalized_title,),
    ).fetchall()
    for row in rows:
        existing_author = row["normalized_author"] or ""
        if not existing_author or not normalized_author or existing_author == normalized_author:
            confidence = "probable" if rows else "needs_review"
            reason = "Normalized title matches"
            if existing_author and normalized_author == existing_author:
                reason += " and author matches."
            else:
                reason += "; author metadata is incomplete."
            return int(row["id"]), confidence, reason
    now = iso_now()
    cur = conn.execute(
        """
        INSERT INTO external_library_works(
            normalized_title,normalized_author,title,author,series,created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?)
        """,
        (normalized_title, normalized_author, title, author, series, now, now),
    )
    return int(cur.lastrowid), "needs_review", "New logical title created from this file's metadata or filename."


def _upsert_item(conn: sqlite3.Connection, root: sqlite3.Row, path: Path, state) -> tuple[bool, int]:
    relative = path.relative_to(Path(root["path"])).as_posix()
    stat = path.stat()
    existing = conn.execute(
        "SELECT * FROM external_library_items WHERE root_id=? AND relative_path=?",
        (root["id"], relative),
    ).fetchone()
    if existing and int(existing["size_bytes"]) == stat.st_size and int(existing["modified_ns"]) == stat.st_mtime_ns and existing["sha256"]:
        conn.execute(
            "UPDATE external_library_items SET availability='online',updated_at=? WHERE id=?",
            (iso_now(), existing["id"]),
        )
        return False, int(existing["id"])
    digest = file_sha256(path, progress=state.add_bytes)
    metadata = metadata_for_file(path)
    role, media_kind = role_for_path(path)
    title = derive_title(path, metadata, role)
    author = normalize_text(metadata.get("author"), 300)
    series = normalize_text(metadata.get("series"), 300)
    normalized_title = normalized_key(title)
    normalized_author = normalized_person(author)
    work_id, confidence, reason = _find_or_create_work(
        conn,
        title=title,
        author=author,
        normalized_title=normalized_title,
        normalized_author=normalized_author,
        series=series,
        sha256=digest,
    )
    manual = conn.execute(
        "SELECT work_id FROM external_library_manual_links WHERE item_id=?",
        (existing["id"],),
    ).fetchone() if existing else None
    if manual:
        work_id = int(manual["work_id"])
        confidence = "confirmed"
        reason = "Manually assigned by the operator."
    now = iso_now()
    values = (
        root["id"], work_id, relative, path.name, path.suffix.casefold(), media_kind, role,
        int(stat.st_size), int(stat.st_mtime_ns), digest, title, normalized_title,
        author, normalized_author, series, normalize_text(metadata.get("volume"), 120),
        normalize_text(metadata.get("narrator"), 300), metadata.get("duration_seconds"),
        normalize_text(metadata.get("identifier"), 500), json.dumps(metadata, ensure_ascii=False),
        "online", confidence, reason, now, now,
    )
    conn.execute(
        """
        INSERT INTO external_library_items(
            root_id,work_id,relative_path,filename,extension,media_kind,role,
            size_bytes,modified_ns,sha256,title,normalized_title,author,normalized_author,
            series,volume,narrator,duration_seconds,identifier,metadata_json,availability,
            match_confidence,match_reason,created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(root_id,relative_path) DO UPDATE SET
            work_id=excluded.work_id,filename=excluded.filename,extension=excluded.extension,
            media_kind=excluded.media_kind,role=excluded.role,size_bytes=excluded.size_bytes,
            modified_ns=excluded.modified_ns,sha256=excluded.sha256,title=excluded.title,
            normalized_title=excluded.normalized_title,author=excluded.author,
            normalized_author=excluded.normalized_author,series=excluded.series,
            volume=excluded.volume,narrator=excluded.narrator,
            duration_seconds=excluded.duration_seconds,identifier=excluded.identifier,
            metadata_json=excluded.metadata_json,availability='online',
            match_confidence=CASE WHEN EXISTS(
                SELECT 1 FROM external_library_manual_links WHERE item_id=external_library_items.id
            ) THEN 'confirmed' ELSE excluded.match_confidence END,
            match_reason=CASE WHEN EXISTS(
                SELECT 1 FROM external_library_manual_links WHERE item_id=external_library_items.id
            ) THEN 'Manually assigned by the operator.' ELSE excluded.match_reason END,
            updated_at=excluded.updated_at
        """,
        values,
    )
    row = conn.execute(
        "SELECT id FROM external_library_items WHERE root_id=? AND relative_path=?",
        (root["id"], relative),
    ).fetchone()
    return True, int(row["id"])


def _associate_companions_by_folder(conn: sqlite3.Connection, root_id: int) -> int:
    rows = conn.execute(
        "SELECT * FROM external_library_items WHERE root_id=? ORDER BY relative_path", (root_id,)
    ).fetchall()
    by_folder: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        folder = str(Path(row["relative_path"]).parent).casefold()
        by_folder.setdefault(folder, []).append(row)
    changed = 0
    for group in by_folder.values():
        primaries = [row for row in group if row["role"] in {"read", "listen"} and row["work_id"]]
        work_ids = {int(row["work_id"]) for row in primaries}
        if len(work_ids) != 1:
            continue
        target = next(iter(work_ids))
        for row in group:
            if row["role"] == "companion" and row["match_confidence"] != "confirmed":
                conn.execute(
                    "UPDATE external_library_items SET work_id=?,match_confidence='probable',match_reason=?,updated_at=? WHERE id=?",
                    (target, "Companion file is stored beside one logical title.", iso_now(), row["id"]),
                )
                changed += 1
    return changed


def scan_location(paths, root_id: int, state=None) -> dict:
    state = state or EXTERNAL_LIBRARY_STATE
    conn = connect_external_library_db(paths)
    started = time.time()
    try:
        root = conn.execute("SELECT * FROM external_library_roots WHERE id=?", (root_id,)).fetchone()
        if not root:
            raise ValueError("Library location not found.")
        if not root["enabled"]:
            raise ValueError("This library location is disabled.")
        folder = _safe_registered_path(root["path"], must_exist=True)
        candidates = list(iter_supported_files(folder))
        state.begin(root_id, root["label"], len(candidates), sum(p.stat().st_size for p in candidates if p.exists()))
        changed = skipped = errors = 0
        seen: set[str] = set()
        for index, path in enumerate(candidates, start=1):
            if state.cancel_requested():
                break
            relative = path.relative_to(folder).as_posix()
            seen.add(relative)
            state.file(index, relative)
            try:
                was_changed, _ = _upsert_item(conn, root, path, state)
                changed += int(was_changed)
                skipped += int(not was_changed)
                conn.commit()
            except Exception as exc:
                errors += 1
                state.error(f"{relative}: {type(exc).__name__}: {exc}")
        missing_rows = conn.execute(
            "SELECT id,relative_path FROM external_library_items WHERE root_id=?", (root_id,)
        ).fetchall()
        removed_catalog = 0
        for row in missing_rows:
            if row["relative_path"] not in seen:
                conn.execute("DELETE FROM external_library_items WHERE id=?", (row["id"],))
                removed_catalog += 1
        companions = _associate_companions_by_folder(conn, root_id)
        _remove_orphan_works(conn)
        now = iso_now()
        conn.execute(
            "UPDATE external_library_roots SET availability='online',last_scan_at=?,last_error='',updated_at=? WHERE id=?",
            (now, now, root_id),
        )
        conn.commit()
        result = {
            "ok": True,
            "root_id": root_id,
            "label": root["label"],
            "supported_files": len(candidates),
            "changed_or_new": changed,
            "unchanged": skipped,
            "catalog_entries_removed_for_missing_files": removed_catalog,
            "companions_associated": companions,
            "errors": errors,
            "elapsed_seconds": round(time.time() - started, 3),
            "original_files_modified": 0,
            "message": "Read-only catalog scan completed. Original files were not copied, moved, renamed, or changed.",
        }
        state.finish(result)
        return result
    except Exception as exc:
        try:
            conn.execute(
                "UPDATE external_library_roots SET availability=?,last_error=?,updated_at=? WHERE id=?",
                ("offline" if not Path(str(root["path"] if 'root' in locals() and root else '')).is_dir() else "error", normalize_text(exc, 500), iso_now(), root_id),
            )
            conn.execute(
                "UPDATE external_library_items SET availability='offline' WHERE root_id=?", (root_id,)
            )
            conn.commit()
        except Exception:
            pass
        state.fail(exc)
        raise
    finally:
        conn.close()


class ExternalLibraryRuntime:
    def __init__(self) -> None:
        self.lock = RLock()
        self.running = False
        self.root_id = 0
        self.label = ""
        self.total = 0
        self.scanned = 0
        self.current_file = ""
        self.total_bytes = 0
        self.hashed_bytes = 0
        self.started_at = ""
        self.started_clock = 0.0
        self.last_result: dict = {}
        self.last_error = ""
        self.errors: list[str] = []
        self._cancel = False

    def begin(self, root_id: int, label: str, total: int, total_bytes: int) -> None:
        with self.lock:
            self.running = True
            self.root_id = int(root_id)
            self.label = str(label)
            self.total = int(total)
            self.scanned = 0
            self.current_file = ""
            self.total_bytes = int(total_bytes)
            self.hashed_bytes = 0
            self.started_at = iso_now()
            self.started_clock = time.time()
            self.last_error = ""
            self.errors = []
            self._cancel = False

    def file(self, scanned: int, relative: str) -> None:
        with self.lock:
            self.scanned = int(scanned)
            self.current_file = relative

    def add_bytes(self, amount: int) -> None:
        with self.lock:
            self.hashed_bytes += int(amount)

    def error(self, message: str) -> None:
        with self.lock:
            self.errors.append(normalize_text(message, 500))
            self.errors = self.errors[-20:]

    def finish(self, result: dict) -> None:
        with self.lock:
            self.running = False
            self.current_file = ""
            self.last_result = dict(result)
            self.last_error = ""
            self._cancel = False

    def fail(self, exc: Exception) -> None:
        with self.lock:
            self.running = False
            self.current_file = ""
            self.last_error = f"{type(exc).__name__}: {exc}"
            self._cancel = False

    def cancel_requested(self) -> bool:
        with self.lock:
            return self._cancel

    def cancel(self) -> tuple[bool, str]:
        with self.lock:
            if not self.running:
                return False, "No external-library scan is running."
            self._cancel = True
            return True, "The scan will stop after the current file."

    def snapshot(self) -> dict:
        with self.lock:
            elapsed = max(0.0, time.time() - self.started_clock) if self.running else float((self.last_result or {}).get("elapsed_seconds") or 0)
            return {
                "running": self.running,
                "root_id": self.root_id,
                "label": self.label,
                "total": self.total,
                "scanned": self.scanned,
                "current_file": self.current_file,
                "total_bytes": self.total_bytes,
                "hashed_bytes": self.hashed_bytes,
                "started_at": self.started_at,
                "elapsed_seconds": round(elapsed, 1),
                "cancel_requested": self._cancel,
                "last_result": dict(self.last_result),
                "last_error": self.last_error,
                "recent_errors": list(self.errors),
            }


EXTERNAL_LIBRARY_STATE = ExternalLibraryRuntime()


def start_location_scan(paths, root_id: int) -> tuple[bool, str]:
    snapshot = EXTERNAL_LIBRARY_STATE.snapshot()
    if snapshot["running"]:
        return False, f"A library-location scan is already running for {snapshot.get('label') or 'another root'}."
    conn = connect_external_library_db(paths)
    try:
        root = conn.execute("SELECT label,enabled,path FROM external_library_roots WHERE id=?", (root_id,)).fetchone()
    finally:
        conn.close()
    if not root:
        return False, "Library location not found."
    if not root["enabled"]:
        return False, "This library location is disabled."
    if not Path(root["path"]).is_dir():
        return False, "This library location is offline."

    def worker():
        try:
            scan_location(paths, root_id, EXTERNAL_LIBRARY_STATE)
        except Exception:
            pass

    thread = Thread(target=worker, name=f"ExternalLibraryScan-{root_id}", daemon=True)
    thread.start()
    return True, f"Read-only catalog scan started for {root['label']}."


def scan_status() -> dict:
    return {"ok": True, **EXTERNAL_LIBRARY_STATE.snapshot()}


def cancel_location_scan() -> dict:
    ok, message = EXTERNAL_LIBRARY_STATE.cancel()
    return {"ok": ok, "message": message}


def _public_item(row: sqlite3.Row) -> dict:
    try:
        metadata = json.loads(row["metadata_json"] or "{}")
    except json.JSONDecodeError:
        metadata = {}
    return {
        "id": int(row["id"]),
        "root_id": int(row["root_id"]),
        "work_id": int(row["work_id"]) if row["work_id"] is not None else None,
        "relative_path": row["relative_path"],
        "filename": row["filename"],
        "extension": row["extension"],
        "media_kind": row["media_kind"],
        "role": row["role"],
        "size_bytes": int(row["size_bytes"]),
        "sha256": row["sha256"],
        "title": row["title"],
        "author": row["author"],
        "series": row["series"],
        "volume": row["volume"],
        "narrator": row["narrator"],
        "duration_seconds": row["duration_seconds"],
        "identifier": row["identifier"],
        "availability": row["availability"],
        "match_confidence": row["match_confidence"],
        "match_reason": row["match_reason"],
        "root_label": row["root_label"] if "root_label" in row.keys() else "",
        "root_path": row["root_path"] if "root_path" in row.keys() else "",
        "metadata": metadata,
    }


def list_works(paths, query: str = "", limit: int = 500) -> dict:
    conn = connect_external_library_db(paths)
    try:
        params: list[object] = []
        where = ""
        text = normalize_text(query, 200).casefold()
        if text:
            where = "WHERE lower(w.title) LIKE ? OR lower(w.author) LIKE ? OR lower(w.series) LIKE ?"
            like = f"%{text}%"
            params.extend([like, like, like])
        params.append(max(1, min(int(limit), 2000)))
        rows = conn.execute(
            f"""
            SELECT w.*,
                   COUNT(i.id) AS file_count,
                   SUM(CASE WHEN i.role='read' THEN 1 ELSE 0 END) AS read_count,
                   SUM(CASE WHEN i.role='listen' THEN 1 ELSE 0 END) AS listen_count,
                   SUM(CASE WHEN i.role='companion' THEN 1 ELSE 0 END) AS companion_count,
                   SUM(CASE WHEN i.availability='online' THEN 1 ELSE 0 END) AS online_count,
                   SUM(CASE WHEN i.match_confidence='needs_review' THEN 1 ELSE 0 END) AS review_count
            FROM external_library_works w
            LEFT JOIN external_library_items i ON i.work_id=w.id
            {where}
            GROUP BY w.id
            HAVING file_count > 0
            ORDER BY w.title COLLATE NOCASE,w.author COLLATE NOCASE
            LIMIT ?
            """,
            params,
        ).fetchall()
        return {
            "ok": True,
            "works": [
                {
                    "id": int(row["id"]),
                    "title": row["title"],
                    "author": row["author"],
                    "series": row["series"],
                    "file_count": int(row["file_count"] or 0),
                    "read_count": int(row["read_count"] or 0),
                    "listen_count": int(row["listen_count"] or 0),
                    "companion_count": int(row["companion_count"] or 0),
                    "online_count": int(row["online_count"] or 0),
                    "review_count": int(row["review_count"] or 0),
                }
                for row in rows
            ],
        }
    finally:
        conn.close()


def work_detail(paths, work_id: int) -> dict:
    conn = connect_external_library_db(paths)
    try:
        work = conn.execute("SELECT * FROM external_library_works WHERE id=?", (work_id,)).fetchone()
        if not work:
            raise ValueError("Logical title not found.")
        rows = conn.execute(
            """
            SELECT i.*,r.label AS root_label,r.path AS root_path
            FROM external_library_items i
            JOIN external_library_roots r ON r.id=i.root_id
            WHERE i.work_id=? ORDER BY i.role,i.extension,i.relative_path
            """,
            (work_id,),
        ).fetchall()
        items = [_public_item(row) for row in rows]
        return {
            "ok": True,
            "work": {
                "id": int(work["id"]),
                "title": work["title"],
                "author": work["author"],
                "series": work["series"],
                "sections": {
                    "read": [item for item in items if item["role"] == "read"],
                    "listen": [item for item in items if item["role"] == "listen"],
                    "companion": [item for item in items if item["role"] == "companion"],
                    "locations": items,
                },
                "items": items,
            },
        }
    finally:
        conn.close()


def assign_item_to_work(paths, item_id: int, work_id: int | None = None, *, split: bool = False) -> dict:
    conn = connect_external_library_db(paths)
    try:
        item = conn.execute("SELECT * FROM external_library_items WHERE id=?", (item_id,)).fetchone()
        if not item:
            raise ValueError("Catalog item not found.")
        if split:
            now = iso_now()
            cur = conn.execute(
                "INSERT INTO external_library_works(normalized_title,normalized_author,title,author,series,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (item["normalized_title"], item["normalized_author"], item["title"], item["author"], item["series"], now, now),
            )
            work_id = int(cur.lastrowid)
        if not work_id:
            raise ValueError("Choose a destination title or use Split into New Title.")
        work = conn.execute("SELECT id FROM external_library_works WHERE id=?", (int(work_id),)).fetchone()
        if not work:
            raise ValueError("Destination title not found.")
        conn.execute(
            "INSERT INTO external_library_manual_links(item_id,work_id,updated_at) VALUES(?,?,?) ON CONFLICT(item_id) DO UPDATE SET work_id=excluded.work_id,updated_at=excluded.updated_at",
            (item_id, int(work_id), iso_now()),
        )
        conn.execute(
            "UPDATE external_library_items SET work_id=?,match_confidence='confirmed',match_reason='Manually assigned by the operator.',updated_at=? WHERE id=?",
            (int(work_id), iso_now(), item_id),
        )
        _remove_orphan_works(conn)
        conn.commit()
        return {"ok": True, "item_id": item_id, "work_id": int(work_id), "match_confidence": "confirmed"}
    finally:
        conn.close()


def resolve_catalog_item_path(paths, item_id: int) -> Path:
    conn = connect_external_library_db(paths)
    try:
        row = conn.execute(
            """
            SELECT i.relative_path,r.path AS root_path,r.enabled
            FROM external_library_items i JOIN external_library_roots r ON r.id=i.root_id
            WHERE i.id=?
            """,
            (item_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise ValueError("Catalog item not found.")
    root = _safe_registered_path(row["root_path"], must_exist=True)
    target = (root / row["relative_path"]).resolve(strict=True)
    if not _is_safe_child(root, target) or not target.is_file():
        raise PermissionError("The catalog item path is unavailable or outside its approved root.")
    return target


def launch_catalog_item(paths, item_id: int) -> dict:
    target = resolve_catalog_item_path(paths, item_id)
    if os.name == "nt":
        os.startfile(str(target))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["xdg-open", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {
        "ok": True,
        "message": f"Opened {target.name} in its installed default application.",
        "original_file_modified": False,
    }


def verify_external_library_environment(paths) -> dict:
    conn = connect_external_library_db(paths)
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
    finally:
        conn.close()
    required = {
        "external_library_roots", "external_library_works",
        "external_library_items", "external_library_manual_links",
    }
    return {
        "ok": required.issubset(tables),
        "database": str(database_path(paths)),
        "tables": sorted(tables),
        "automatic_drive_crawling": False,
        "original_files_modified": 0,
    }
