from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sqlite3
from threading import RLock
import tempfile
import time
from urllib.parse import urljoin, urlparse, urlunparse
import urllib.error
import urllib.request
from uuid import uuid4

RESEARCH_SCHEMA_VERSION = 1
RESEARCH_SHELF = "Research"
RESEARCH_RELATIVE_ROOT = Path("Research")
RESEARCH_FETCH_TIMEOUT_SECONDS = 12
RESEARCH_MAX_REDIRECTS = 5
RESEARCH_MAX_HTML_BYTES = 4 * 1024 * 1024
RESEARCH_MAX_TEXT_BYTES = 4 * 1024 * 1024
RESEARCH_PREVIEW_TEXT_CHARS = 16000
RESEARCH_USER_AGENT = "KayocksStudy/1.6 ControlledResearchDesk"
RESEARCH_POLICY = {
    "session_only": True,
    "network_off_by_default": True,
    "automatic_search": False,
    "background_crawling": False,
    "telemetry": False,
    "prefetch": False,
    "cookies": False,
    "javascript": False,
    "forms": False,
}


def iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _slug(value: str, limit: int = 72) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", " ", str(value or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip().replace(" ", "_")
    return (cleaned[:limit] or "saved_research").strip("._") or "saved_research"


class ResearchSessionState:
    def __init__(self) -> None:
        self.lock = RLock()
        self.enabled = False
        self.status = "OFFLINE"
        self.last_error = ""
        self.previews: dict[str, dict] = {}

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "enabled": self.enabled,
                "status": self.status,
                "last_error": self.last_error,
                "preview_count": len(self.previews),
                "policy": dict(RESEARCH_POLICY),
            }

    def enable(self) -> dict:
        with self.lock:
            self.enabled = True
            self.status = "ONLINE RESEARCH ENABLED"
            self.last_error = ""
            return self.snapshot()

    def stop(self) -> dict:
        with self.lock:
            self.enabled = False
            self.status = "STOPPED"
            self.last_error = ""
            self.previews.clear()
            return self.snapshot()

    def require_enabled(self) -> None:
        with self.lock:
            if not self.enabled:
                raise PermissionError(
                    "Online Research is Off. Enable it for this Study session first."
                )

    def set_status(self, status: str, error: str = "") -> None:
        with self.lock:
            self.status = status
            self.last_error = error

    def store_preview(self, preview: dict) -> str:
        with self.lock:
            preview_id = str(preview.get("preview_id") or uuid4().hex)
            preview["preview_id"] = preview_id
            self.previews[preview_id] = preview
            while len(self.previews) > 5:
                oldest = next(iter(self.previews))
                self.previews.pop(oldest, None)
            return preview_id

    def get_preview(self, preview_id: str) -> dict | None:
        with self.lock:
            return self.previews.get(str(preview_id or "").strip())

    def discard(self, preview_id: str) -> bool:
        with self.lock:
            return self.previews.pop(str(preview_id or "").strip(), None) is not None


RESEARCH_STATE = ResearchSessionState()
_MIGRATION_LOCK = RLock()


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return bool(row)


def _base_counts(conn: sqlite3.Connection) -> dict:
    result = {"documents": 0, "pages": 0}
    if _table_exists(conn, "documents"):
        result["documents"] = int(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
    if _table_exists(conn, "pages"):
        result["pages"] = int(conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0])
    return result


def initialize_research_schema(
    conn: sqlite3.Connection,
    *,
    database_path: Path,
    reports_dir: Path,
    database_preexisted: bool,
) -> dict:
    """Apply the additive V1.6 schema once, with a verified database backup."""
    with _MIGRATION_LOCK:
        if _table_exists(conn, "research_captures") and _table_exists(conn, "research_segments"):
            return {"migrated": False, "schema": RESEARCH_SCHEMA_VERSION}

        before = _base_counts(conn)
        backup_path = None
        backup_sha256 = ""
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        receipt_dir = reports_dir / "V1_6_ResearchDesk"
        receipt_dir.mkdir(parents=True, exist_ok=True)

        if database_preexisted and database_path.exists():
            backup_dir = database_path.parent / "Backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"bibliotheca_pre_v1_6_{stamp}.sqlite3"
            destination = sqlite3.connect(str(backup_path))
            try:
                conn.backup(destination)
            finally:
                destination.close()
            backup_sha256 = file_sha256(backup_path)

        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_captures(
                    id INTEGER PRIMARY KEY,
                    canonical_url TEXT NOT NULL,
                    original_url TEXT NOT NULL,
                    final_url TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL DEFAULT '',
                    published_at TEXT NOT NULL DEFAULT '',
                    retrieved_at TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    response_size INTEGER NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    readable_sha256 TEXT NOT NULL,
                    capture_version INTEGER NOT NULL DEFAULT 1,
                    origin_kind TEXT NOT NULL,
                    search_query TEXT NOT NULL DEFAULT '',
                    original_path TEXT NOT NULL,
                    readable_path TEXT NOT NULL,
                    metadata_path TEXT NOT NULL,
                    notes_path TEXT NOT NULL,
                    previous_capture_id INTEGER REFERENCES research_captures(id),
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_segments(
                    id INTEGER PRIMARY KEY,
                    capture_id INTEGER NOT NULL REFERENCES research_captures(id)
                        ON DELETE CASCADE,
                    segment_number INTEGER NOT NULL,
                    heading TEXT NOT NULL DEFAULT '',
                    text TEXT NOT NULL,
                    text_chars INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(capture_id, segment_number)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_research_canonical_url ON research_captures(canonical_url)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_research_final_url ON research_captures(final_url)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_research_content_hash ON research_captures(content_sha256)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_research_readable_hash ON research_captures(readable_sha256)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_research_segments_capture ON research_segments(capture_id,segment_number)"
            )
            if _table_exists(conn, "metadata"):
                conn.execute(
                    "INSERT OR REPLACE INTO metadata(key,value) VALUES('research_schema',?)",
                    (str(RESEARCH_SCHEMA_VERSION),),
                )
            after = _base_counts(conn)
            if before != after:
                raise RuntimeError(
                    f"Existing Bibliotheca record counts changed during migration: {before} -> {after}"
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        receipt = {
            "schema": "foxai.kayocks_study.research_migration.v1",
            "created": iso_now(),
            "result": "additive_migration_verified",
            "database": str(database_path),
            "database_backup": str(backup_path) if backup_path else "new_database_no_prior_file",
            "database_backup_sha256": backup_sha256,
            "tables_added": ["research_captures", "research_segments"],
            "existing_counts_before": before,
            "existing_counts_after": after,
            "existing_records_preserved": before == after,
            "pdf_files_modified": 0,
            "network_used": False,
        }
        receipt_path = receipt_dir / f"{stamp}_research_schema_migration.json"
        receipt["receipt_path"] = str(receipt_path)
        receipt_path.write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if _table_exists(conn, "metadata"):
            conn.execute(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES('research_migration_receipt',?)",
                (str(receipt_path),),
            )
            conn.commit()
        return {"migrated": True, **receipt}


def research_summary(conn: sqlite3.Connection) -> dict:
    if not _table_exists(conn, "research_captures"):
        return {"saved": 0, "segments": 0, "revisions": 0}
    row = conn.execute(
        """
        SELECT COUNT(*) saved,
               COALESCE(SUM(CASE WHEN capture_version>1 THEN 1 ELSE 0 END),0) revisions
        FROM research_captures
        """
    ).fetchone()
    segments = int(conn.execute("SELECT COUNT(*) FROM research_segments").fetchone()[0])
    return {
        "saved": int(row["saved"] if hasattr(row, "keys") else row[0]),
        "segments": segments,
        "revisions": int(row["revisions"] if hasattr(row, "keys") else row[1]),
    }


def canonicalize_url(value: str) -> str:
    parsed = urlparse(str(value or "").strip())
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if not scheme or not host:
        return str(value or "").strip()
    port = parsed.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    path = parsed.path or "/"
    return urlunparse((scheme, netloc, path, "", parsed.query, ""))


def _forbidden_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_url(value: str) -> dict:
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are allowed.")
    if not parsed.hostname:
        raise ValueError("The URL must include a host name.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded credentials are not allowed.")
    host = parsed.hostname.rstrip(".")
    if host.casefold() in {"localhost", "localhost.localdomain"}:
        raise ValueError("Localhost targets are not allowed.")
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    try:
        addresses = sorted(
            {
                item[4][0]
                for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            }
        )
    except socket.gaierror as exc:
        raise ValueError(f"The host could not be resolved: {exc}") from exc
    if not addresses:
        raise ValueError("The host did not resolve to an address.")
    blocked = [address for address in addresses if _forbidden_ip(address)]
    if blocked:
        raise ValueError(
            "Private, loopback, link-local, reserved, and multicast targets are not allowed."
        )
    return {
        "url": raw,
        "canonical_url": canonicalize_url(raw),
        "host": host,
        "addresses": addresses,
    }


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.redirects = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.redirects += 1
        if self.redirects > RESEARCH_MAX_REDIRECTS:
            raise urllib.error.HTTPError(
                req.full_url, code, "Too many redirects", headers, fp
            )
        absolute = urljoin(req.full_url, newurl)
        validate_public_url(absolute)
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def fetch_public_source(url: str) -> dict:
    validated = validate_public_url(url)
    redirect_handler = _SafeRedirectHandler()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), redirect_handler
    )
    request = urllib.request.Request(
        validated["url"],
        headers={
            "User-Agent": RESEARCH_USER_AGENT,
            "Accept": "text/html,text/plain;q=0.9,*/*;q=0.2",
            "Accept-Encoding": "identity",
        },
        method="GET",
    )
    with opener.open(request, timeout=RESEARCH_FETCH_TIMEOUT_SECONDS) as response:
        final_url = response.geturl()
        validate_public_url(final_url)
        content_type_header = str(response.headers.get("Content-Type") or "")
        media_type = content_type_header.split(";", 1)[0].strip().lower()
        if media_type not in {"text/html", "text/plain"}:
            if media_type == "application/pdf":
                raise ValueError(
                    "Remote PDF capture is not enabled in V1.6. Use the existing safe PDF import path."
                )
            raise ValueError(
                f"Unsupported response type: {media_type or 'unknown'}. V1.6 supports HTML and plain text."
            )
        maximum = RESEARCH_MAX_HTML_BYTES if media_type == "text/html" else RESEARCH_MAX_TEXT_BYTES
        declared = response.headers.get("Content-Length")
        if declared:
            try:
                if int(declared) > maximum:
                    raise ValueError("The response exceeds the Research Desk size limit.")
            except ValueError as exc:
                if "exceeds" in str(exc):
                    raise
        chunks = []
        total = 0
        while True:
            block = response.read(min(65536, maximum + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > maximum:
                raise ValueError("The response exceeds the Research Desk size limit.")
        return {
            "original_url": validated["url"],
            "final_url": final_url,
            "canonical_url": canonicalize_url(final_url),
            "domain": urlparse(final_url).hostname or "",
            "content_type": media_type,
            "content_type_header": content_type_header,
            "response_size": total,
            "raw_bytes": b"".join(chunks),
            "redirect_count": redirect_handler.redirects,
        }


class ReadableHTMLParser(HTMLParser):
    BLOCKS = {"p", "li", "blockquote", "pre", "h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP = {"script", "style", "noscript", "svg", "canvas", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.current_tag = ""
        self.current: list[str] = []
        self.blocks: list[tuple[str, str]] = []
        self.title_parts: list[str] = []
        self.in_title = False
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            data = {str(k or "").lower(): str(v or "") for k, v in attrs}
            key = (data.get("name") or data.get("property") or "").lower()
            value = data.get("content") or ""
            if key and value:
                self.meta[key] = value.strip()
        if tag in self.BLOCKS:
            self._flush()
            self.current_tag = tag

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag == "title":
            self.in_title = False
        if tag in self.BLOCKS:
            self._flush()
            self.current_tag = ""

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        cleaned = re.sub(r"\s+", " ", data or " ").strip()
        if not cleaned:
            return
        if self.in_title:
            self.title_parts.append(cleaned)
        if self.current_tag:
            self.current.append(cleaned)

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", " ".join(self.current)).strip()
        if text:
            self.blocks.append((self.current_tag or "p", text))
        self.current = []

    def finish(self) -> None:
        self._flush()


def _decode_source(raw: bytes, content_type_header: str = "") -> str:
    match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type_header, re.I)
    candidates = [match.group(1)] if match else []
    candidates += ["utf-8", "windows-1252", "latin-1"]
    for encoding in candidates:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def extract_readable(raw: bytes, content_type: str, final_url: str, content_type_header: str = "") -> dict:
    text = _decode_source(raw, content_type_header)
    title = Path(urlparse(final_url).path).stem.replace("-", " ").replace("_", " ").strip()
    author = ""
    published_at = ""
    ordered: list[tuple[str, str]] = []
    if content_type == "text/html":
        parser = ReadableHTMLParser()
        parser.feed(text)
        parser.finish()
        ordered = parser.blocks
        parsed_title = re.sub(r"\s+", " ", " ".join(parser.title_parts)).strip()
        title = parsed_title or parser.meta.get("og:title") or title or urlparse(final_url).hostname or "Saved research"
        author = parser.meta.get("author") or parser.meta.get("article:author") or ""
        published_at = (
            parser.meta.get("article:published_time")
            or parser.meta.get("date")
            or parser.meta.get("datepublished")
            or ""
        )
    else:
        lines = [line.strip() for line in text.splitlines()]
        for line in lines:
            if not line:
                continue
            kind = "h2" if len(line) <= 100 and not re.search(r"[.!?]$", line) else "p"
            ordered.append((kind, line))
        if ordered:
            title = ordered[0][1][:180]

    segments: list[dict] = []
    current_heading = title
    current_parts: list[str] = []

    def flush() -> None:
        nonlocal current_parts
        combined = "\n\n".join(part for part in current_parts if part).strip()
        if combined:
            segments.append(
                {
                    "segment_number": len(segments) + 1,
                    "heading": current_heading or title,
                    "text": combined,
                }
            )
        current_parts = []

    for kind, value in ordered:
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            continue
        if kind.startswith("h"):
            flush()
            current_heading = value[:240]
        else:
            current_parts.append(value)
    flush()

    if not segments:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if cleaned:
            segments = [{"segment_number": 1, "heading": title, "text": cleaned}]
    if not segments:
        raise ValueError("No readable text could be extracted from this source.")

    readable_text = "\n\n".join(
        f"## {item['heading']}\n\n{item['text']}" for item in segments
    ).strip()
    return {
        "title": title[:300],
        "author": author[:300],
        "published_at": published_at[:120],
        "segments": segments,
        "readable_text": readable_text,
    }


def _duplicate_status(conn: sqlite3.Connection, preview: dict) -> dict:
    if not _table_exists(conn, "research_captures"):
        return {"status": "new", "existing": None}
    row = conn.execute(
        """
        SELECT * FROM research_captures
        WHERE content_sha256=? OR readable_sha256=?
        ORDER BY retrieved_at DESC,id DESC LIMIT 1
        """,
        (preview["content_sha256"], preview["readable_sha256"]),
    ).fetchone()
    if row:
        return {"status": "exact_duplicate", "existing": dict(row)}
    row = conn.execute(
        """
        SELECT * FROM research_captures
        WHERE canonical_url=? OR final_url=?
        ORDER BY capture_version DESC,retrieved_at DESC,id DESC LIMIT 1
        """,
        (preview["canonical_url"], preview["final_url"]),
    ).fetchone()
    if row:
        return {"status": "revision_available", "existing": dict(row)}
    return {"status": "new", "existing": None}


def preview_from_bytes(
    paths,
    *,
    original_url: str,
    final_url: str,
    raw_bytes: bytes,
    content_type: str,
    content_type_header: str = "",
    origin_kind: str = "direct_url",
    search_query: str = "",
    retrieved_at: str = "",
) -> dict:
    extracted = extract_readable(raw_bytes, content_type, final_url, content_type_header)
    readable_bytes = extracted["readable_text"].encode("utf-8")
    preview = {
        "preview_id": uuid4().hex,
        "original_url": original_url,
        "final_url": final_url,
        "canonical_url": canonicalize_url(final_url),
        "domain": urlparse(final_url).hostname or "",
        "retrieved_at": retrieved_at or iso_now(),
        "content_type": content_type,
        "response_size": len(raw_bytes),
        "content_sha256": sha256_bytes(raw_bytes),
        "readable_sha256": sha256_bytes(readable_bytes),
        "title": extracted["title"],
        "author": extracted["author"],
        "published_at": extracted["published_at"],
        "readable_text": extracted["readable_text"],
        "segments": extracted["segments"],
        "origin_kind": origin_kind,
        "search_query": search_query,
        "raw_bytes": raw_bytes,
        "proposed_shelf": RESEARCH_SHELF,
        "proposed_filename": _slug(extracted["title"]),
    }
    conn = sqlite3.connect(str(paths.database), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        preview["duplicate"] = _duplicate_status(conn, preview)
    finally:
        conn.close()
    RESEARCH_STATE.store_preview(preview)
    return preview


def public_preview(preview: dict) -> dict:
    existing = dict((preview.get("duplicate") or {}).get("existing") or {})
    if existing:
        existing = {
            key: existing.get(key)
            for key in ("id", "title", "retrieved_at", "capture_version", "readable_path")
        }
    return {
        "preview_id": preview.get("preview_id"),
        "title": preview.get("title"),
        "original_url": preview.get("original_url"),
        "final_url": preview.get("final_url"),
        "domain": preview.get("domain"),
        "retrieved_at": preview.get("retrieved_at"),
        "content_type": preview.get("content_type"),
        "response_size": preview.get("response_size"),
        "content_sha256": preview.get("content_sha256"),
        "readable_sha256": preview.get("readable_sha256"),
        "author": preview.get("author"),
        "published_at": preview.get("published_at"),
        "readable_preview": str(preview.get("readable_text") or "")[:RESEARCH_PREVIEW_TEXT_CHARS],
        "proposed_shelf": preview.get("proposed_shelf"),
        "proposed_filename": preview.get("proposed_filename"),
        "duplicate_status": (preview.get("duplicate") or {}).get("status", "new"),
        "existing": existing or None,
        "origin_kind": preview.get("origin_kind"),
        "search_query": preview.get("search_query"),
    }


def preview_url(paths, url: str, *, origin_kind: str = "direct_url", search_query: str = "") -> dict:
    RESEARCH_STATE.require_enabled()
    RESEARCH_STATE.set_status("FETCHING")
    try:
        fetched = fetch_public_source(url)
        preview = preview_from_bytes(
            paths,
            original_url=fetched["original_url"],
            final_url=fetched["final_url"],
            raw_bytes=fetched["raw_bytes"],
            content_type=fetched["content_type"],
            content_type_header=fetched["content_type_header"],
            origin_kind=origin_kind,
            search_query=search_query,
        )
        RESEARCH_STATE.set_status("ONLINE RESEARCH ENABLED")
        return public_preview(preview)
    except Exception as exc:
        RESEARCH_STATE.set_status("ERROR", f"{type(exc).__name__}: {exc}")
        raise


class SearchProviderAdapter:
    provider_id = "base"

    def available(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> list[dict]:
        raise RuntimeError("Search provider is unavailable.")


class UnavailableSearchProvider(SearchProviderAdapter):
    provider_id = "unavailable"


SEARCH_PROVIDER: SearchProviderAdapter = UnavailableSearchProvider()


def search_web(query: str) -> dict:
    RESEARCH_STATE.require_enabled()
    value = str(query or "").strip()
    if not value:
        raise ValueError("Enter a web search query.")
    if not SEARCH_PROVIDER.available():
        return {
            "ok": False,
            "provider": SEARCH_PROVIDER.provider_id,
            "results": [],
            "message": (
                "No installed search-provider adapter is available without adding a package. "
                "Direct-URL research remains fully available; no search results were fabricated."
            ),
        }
    results = SEARCH_PROVIDER.search(value, limit=5)
    return {"ok": True, "provider": SEARCH_PROVIDER.provider_id, "results": results[:5]}


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _readable_markdown(preview: dict) -> str:
    lines = [
        f"# {preview['title']}",
        "",
        f"Original URL: {preview['original_url']}",
        f"Final URL: {preview['final_url']}",
        f"Captured: {preview['retrieved_at']}",
        f"Author: {preview.get('author') or 'Not reliably available'}",
        f"Published: {preview.get('published_at') or 'Not reliably available'}",
        f"Content SHA-256: {preview['content_sha256']}",
        f"Readable SHA-256: {preview['readable_sha256']}",
        "",
        "---",
        "",
        preview["readable_text"],
        "",
    ]
    return "\n".join(lines)


def save_preview(paths, preview_id: str, *, notes: str = "", save_new_revision: bool = False) -> dict:
    preview = RESEARCH_STATE.get_preview(preview_id)
    if not preview:
        raise ValueError("The capture preview is no longer available in this session.")
    conn = sqlite3.connect(str(paths.database), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    duplicate = _duplicate_status(conn, preview)
    if duplicate["status"] in {"exact_duplicate", "revision_available"} and not save_new_revision:
        conn.close()
        return {
            "ok": False,
            "duplicate": True,
            "duplicate_status": duplicate["status"],
            "existing": dict(duplicate.get("existing") or {}),
            "message": (
                "This source already exists. Open the existing capture or use Save New Revision deliberately."
                if duplicate["status"] == "exact_duplicate"
                else "A prior capture of this URL exists. Use Save New Revision to retain the changed version."
            ),
        }

    previous = duplicate.get("existing")
    previous_id = int(previous["id"]) if previous else None
    version_row = conn.execute(
        "SELECT COALESCE(MAX(capture_version),0) FROM research_captures WHERE canonical_url=?",
        (preview["canonical_url"],),
    ).fetchone()
    version = int(version_row[0] or 0) + 1
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    folder = (
        paths.library
        / RESEARCH_RELATIVE_ROOT
        / _slug(preview["title"])
        / f"capture_{stamp}_v{version}_{preview['content_sha256'][:8]}"
    )
    if folder.exists():
        folder = folder.with_name(folder.name + "_" + uuid4().hex[:6])
    folder.mkdir(parents=True, exist_ok=False)

    extension = ".html" if preview["content_type"] == "text/html" else ".txt"
    original_path = folder / ("original" + extension)
    readable_path = folder / "readable.md"
    metadata_path = folder / "metadata.json"
    notes_path = folder / "notes.md"
    readable = _readable_markdown(preview)
    metadata = {
        "schema": "foxai.kayocks_study.research_capture.v1",
        "title": preview["title"],
        "original_url": preview["original_url"],
        "final_url": preview["final_url"],
        "canonical_url": preview["canonical_url"],
        "domain": preview["domain"],
        "author": preview.get("author") or "",
        "published_at": preview.get("published_at") or "",
        "retrieved_at": preview["retrieved_at"],
        "content_type": preview["content_type"],
        "response_size": preview["response_size"],
        "content_sha256": preview["content_sha256"],
        "readable_sha256": preview["readable_sha256"],
        "capture_version": version,
        "origin_kind": preview.get("origin_kind") or "direct_url",
        "search_query": preview.get("search_query") or "",
        "previous_capture_id": previous_id,
        "original_path": str(original_path.relative_to(paths.library).as_posix()),
        "readable_path": str(readable_path.relative_to(paths.library).as_posix()),
        "metadata_path": str(metadata_path.relative_to(paths.library).as_posix()),
        "notes_path": str(notes_path.relative_to(paths.library).as_posix()),
    }

    try:
        _write_atomic(original_path, preview["raw_bytes"])
        _write_atomic(readable_path, readable.encode("utf-8"))
        _write_atomic(metadata_path, (json.dumps(metadata, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
        _write_atomic(notes_path, str(notes or "").encode("utf-8"))
        cursor = conn.execute(
            """
            INSERT INTO research_captures(
                canonical_url,original_url,final_url,domain,title,author,published_at,
                retrieved_at,content_type,response_size,content_sha256,readable_sha256,
                capture_version,origin_kind,search_query,original_path,readable_path,
                metadata_path,notes_path,previous_capture_id,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                preview["canonical_url"], preview["original_url"], preview["final_url"],
                preview["domain"], preview["title"], preview.get("author") or "",
                preview.get("published_at") or "", preview["retrieved_at"],
                preview["content_type"], int(preview["response_size"]),
                preview["content_sha256"], preview["readable_sha256"], version,
                preview.get("origin_kind") or "direct_url", preview.get("search_query") or "",
                metadata["original_path"], metadata["readable_path"], metadata["metadata_path"],
                metadata["notes_path"], previous_id, iso_now(),
            ),
        )
        capture_id = int(cursor.lastrowid)
        for segment in preview["segments"]:
            conn.execute(
                """
                INSERT INTO research_segments(capture_id,segment_number,heading,text,text_chars)
                VALUES(?,?,?,?,?)
                """,
                (
                    capture_id, int(segment["segment_number"]), str(segment.get("heading") or ""),
                    str(segment.get("text") or ""), len(str(segment.get("text") or "")),
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        shutil.rmtree(folder, ignore_errors=True)
        raise
    finally:
        conn.close()

    RESEARCH_STATE.discard(preview_id)
    return {
        "ok": True,
        "capture_id": capture_id,
        "title": preview["title"],
        "capture_version": version,
        "previous_capture_id": previous_id,
        "folder": str(folder),
        "original_path": str(original_path),
        "readable_path": str(readable_path),
        "metadata_path": str(metadata_path),
        "notes_path": str(notes_path),
        "message": "Saved to The Bibliotheca Research shelf with separate original, readable, metadata, and notes layers.",
    }


def list_saved(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    if not _table_exists(conn, "research_captures"):
        return []
    rows = conn.execute(
        """
        SELECT id,title,domain,original_url,final_url,author,published_at,retrieved_at,
               content_type,response_size,content_sha256,readable_sha256,capture_version,
               origin_kind,search_query,original_path,readable_path,metadata_path,notes_path,
               previous_capture_id
        FROM research_captures
        ORDER BY retrieved_at DESC,id DESC LIMIT ?
        """,
        (max(1, min(int(limit), 500)),),
    ).fetchall()
    return [dict(row) for row in rows]


def research_segment_source(conn: sqlite3.Connection, capture_id: int, segment_number: int, query: str = "") -> dict | None:
    if not _table_exists(conn, "research_segments"):
        return None
    row = conn.execute(
        """
        SELECT c.id research_id,c.title,c.readable_path,c.original_url,c.retrieved_at,
               s.segment_number,s.heading,s.text
        FROM research_segments s
        JOIN research_captures c ON c.id=s.capture_id
        WHERE c.id=? AND s.segment_number=?
        """,
        (int(capture_id), int(segment_number)),
    ).fetchone()
    if not row:
        return None
    item = dict(row)
    captured = str(item["retrieved_at"] or "")[:10]
    heading = str(item["heading"] or "Indexed segment")
    return {
        "source_kind": "research",
        "research_id": int(item["research_id"]),
        "document_id": None,
        "title": item["title"],
        "rel_path": item["readable_path"],
        "shelf": RESEARCH_SHELF,
        "page_number": 0,
        "segment_number": int(item["segment_number"]),
        "section_heading": heading,
        "capture_date": captured,
        "original_url": item["original_url"],
        "snippet": _plain_snippet(item["text"], query),
        "text": item["text"],
        "text_status": "research_capture",
        "is_ocr_copy": False,
        "citation": f"[{item['title']}, captured {captured}, {heading}, segment {item['segment_number']}]",
    }


def _query_tokens(query: str) -> list[str]:
    return [item.casefold() for item in re.findall(r"[A-Za-z0-9][A-Za-z0-9'_-]*", query or "")[:12]]


def _plain_snippet(text: str, query: str, limit: int = 420) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    tokens = _query_tokens(query)
    lower = cleaned.casefold()
    positions = [lower.find(token) for token in tokens if lower.find(token) >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - 120)
    end = min(len(cleaned), start + limit)
    snippet = cleaned[start:end]
    return ("…" if start else "") + snippet + ("…" if end < len(cleaned) else "")


def search_research(conn: sqlite3.Connection, query: str, limit: int = 30) -> list[dict]:
    if not _table_exists(conn, "research_segments"):
        return []
    tokens = _query_tokens(query)
    if not tokens:
        return []
    clauses = ["LOWER(s.text || ' ' || s.heading || ' ' || c.title) LIKE ?" for _ in tokens]
    params = [f"%{token}%" for token in tokens]
    sql = f"""
        SELECT c.id research_id,c.title,c.readable_path,c.original_url,c.retrieved_at,
               s.segment_number,s.heading,s.text
        FROM research_segments s
        JOIN research_captures c ON c.id=s.capture_id
        WHERE {' AND '.join(clauses)}
        ORDER BY c.retrieved_at DESC,c.id DESC,s.segment_number
        LIMIT ?
    """
    params.append(max(1, min(int(limit), 80)))
    rows = conn.execute(sql, params).fetchall()
    results = []
    for row in rows:
        item = dict(row)
        captured = str(item["retrieved_at"] or "")[:10]
        heading = str(item["heading"] or "Indexed segment")
        results.append(
            {
                "source_kind": "research",
                "research_id": int(item["research_id"]),
                "document_id": None,
                "title": item["title"],
                "rel_path": item["readable_path"],
                "shelf": RESEARCH_SHELF,
                "page_number": 0,
                "segment_number": int(item["segment_number"]),
                "section_heading": heading,
                "capture_date": captured,
                "original_url": item["original_url"],
                "snippet": _plain_snippet(item["text"], query),
                "text": item["text"],
                "text_status": "research_capture",
                "is_ocr_copy": False,
                "citation": f"[{item['title']}, captured {captured}, {heading}, segment {item['segment_number']}]",
            }
        )
    return results


def research_file(conn: sqlite3.Connection, library: Path, capture_id: int, kind: str) -> Path | None:
    column = {"readable": "readable_path", "original": "original_path", "metadata": "metadata_path", "notes": "notes_path"}.get(kind)
    if not column or not _table_exists(conn, "research_captures"):
        return None
    row = conn.execute(f"SELECT {column} path FROM research_captures WHERE id=?", (int(capture_id),)).fetchone()
    if not row:
        return None
    candidate = (library / str(row["path"])).resolve()
    try:
        candidate.relative_to(library.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def update_notes(conn: sqlite3.Connection, library: Path, capture_id: int, notes: str) -> dict:
    path = research_file(conn, library, capture_id, "notes")
    if not path:
        raise ValueError("Saved research notes file was not found.")
    _write_atomic(path, str(notes or "").encode("utf-8"))
    return {"ok": True, "capture_id": int(capture_id), "notes_path": str(path), "message": "Research notes saved separately."}
