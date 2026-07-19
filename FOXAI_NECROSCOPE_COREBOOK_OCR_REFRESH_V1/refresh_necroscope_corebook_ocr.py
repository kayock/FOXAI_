from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent
VENDOR_DIR = PACKAGE_DIR / "vendor"
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

from pypdf import PdfReader
import pypdf

COREBOOK_KEY = "masterbook_core"
COREBOOK_TITLE = "MasterBook Corebook"
OCR_FILENAME = "Masterbook Corebook_OCR_searchable.pdf"

DECK_TERMS = [
    "MasterDeck", "Master Deck", "card", "cards", "draw", "discard",
    "hand", "subplot", "play a card", "hero card", "drama card", "action card",
]

RULE_TERMS = [
    "Bonus Number", "Value Chart", "result points", "difficulty number",
    "effect value", "two ten-sided dice", "2d10",
    "character creation", "skill points", "character points",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_text(value: str) -> str:
    value = value.replace("\x00", "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{4,}", "\n\n\n", value)
    return value.strip()


def extract_page(page: Any) -> tuple[str, str]:
    try:
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            text = page.extract_text() or ""
        return clean_text(text), ""
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"


def has_fts(connection: sqlite3.Connection) -> bool:
    return bool(connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pages_fts'"
    ).fetchone())


def validate_schema(connection: sqlite3.Connection) -> None:
    required = {"books", "pages"}
    found = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    missing = sorted(required - found)
    if missing:
        raise RuntimeError("Missing index tables: " + ", ".join(missing))


def replace_corebook(connection: sqlite3.Connection, source: Path, indexed_at: str) -> dict[str, Any]:
    reader = PdfReader(str(source), strict=False)
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception as exc:
            raise RuntimeError("OCR corebook could not be decrypted.") from exc

    fts = has_fts(connection)
    page_count = len(reader.pages)
    source_hash = sha256_file(source)

    connection.execute("DELETE FROM pages WHERE book_key=?", (COREBOOK_KEY,))
    if fts:
        connection.execute("DELETE FROM pages_fts WHERE book_key=?", (COREBOOK_KEY,))
    connection.execute("DELETE FROM books WHERE book_key=?", (COREBOOK_KEY,))

    connection.execute(
        """
        INSERT INTO books(
            book_key,title,filename,source_path,size_bytes,
            sha256,page_count,indexed_at
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            COREBOOK_KEY, COREBOOK_TITLE, source.name, str(source),
            source.stat().st_size, source_hash, page_count, indexed_at,
        ),
    )

    total_chars = 0
    low_text_pages = 0
    error_pages = 0

    print("Opening OCR copy read-only:", source.name)
    print("Pages reported:", page_count)

    for page_number, page in enumerate(reader.pages, start=1):
        text, error = extract_page(page)
        char_count = len(text)
        low_text = 1 if len(re.sub(r"\s+", "", text)) < 80 else 0

        connection.execute(
            """
            INSERT INTO pages(
                book_key,title,page_number,text,char_count,
                low_text,extraction_error
            ) VALUES(?,?,?,?,?,?,?)
            """,
            (
                COREBOOK_KEY, COREBOOK_TITLE, page_number, text,
                char_count, low_text, error,
            ),
        )
        if fts:
            connection.execute(
                """
                INSERT INTO pages_fts(book_key,title,page_number,text)
                VALUES(?,?,?,?)
                """,
                (COREBOOK_KEY, COREBOOK_TITLE, page_number, text),
            )

        total_chars += char_count
        low_text_pages += low_text
        error_pages += 1 if error else 0

        if page_number % 20 == 0 or page_number == page_count:
            print(
                f"  pages {page_number}/{page_count} | "
                f"characters {total_chars:,} | low-text {low_text_pages}"
            )

    return {
        "filename": source.name,
        "source_path": str(source),
        "sha256": source_hash,
        "size_bytes": source.stat().st_size,
        "page_count": page_count,
        "characters": total_chars,
        "low_text_pages": low_text_pages,
        "error_pages": error_pages,
        "fts_updated": fts,
    }


def find_hits(connection: sqlite3.Connection, terms: list[str], limit: int = 40) -> dict[str, list[int]]:
    output: dict[str, list[int]] = {}
    for term in terms:
        rows = connection.execute(
            """
            SELECT page_number
            FROM pages
            WHERE book_key=?
              AND instr(lower(text), lower(?)) > 0
            ORDER BY page_number
            LIMIT ?
            """,
            (COREBOOK_KEY, term, limit),
        ).fetchall()
        if rows:
            output[term] = [int(row[0]) for row in rows]
    return output


def select_pages(deck_hits: dict[str, list[int]], rule_hits: dict[str, list[int]], page_count: int) -> list[int]:
    selected: set[int] = set()
    for pages in deck_hits.values():
        for page in pages[:20]:
            for candidate in range(page - 1, page + 2):
                if 1 <= candidate <= page_count:
                    selected.add(candidate)
    for pages in rule_hits.values():
        for page in pages[:8]:
            if 1 <= page <= page_count:
                selected.add(page)
    return sorted(selected)[:80]


def write_packet(connection: sqlite3.Connection, path: Path, refresh: dict[str, Any], deck_hits: dict[str, list[int]], rule_hits: dict[str, list[int]], built: str) -> None:
    pages = select_pages(deck_hits, rule_hits, int(refresh["page_count"]))
    lines = [
        "# MasterBook Corebook OCR Rules Packet",
        "",
        f"- Built: `{built}`",
        f"- OCR source: `{refresh['filename']}`",
        f"- Source SHA-256: `{refresh['sha256']}`",
        f"- Pages: `{refresh['page_count']}`",
        f"- Extracted characters: `{refresh['characters']:,}`",
        f"- Low-text pages: `{refresh['low_text_pages']}`",
        f"- Extraction-error pages: `{refresh['error_pages']}`",
        "- Source handling: read-only",
        "- Page references are PDF page numbers from the OCR copy.",
        "",
        "## MasterDeck and Card Search Leads",
        "",
    ]
    if deck_hits:
        for term, pages_found in deck_hits.items():
            lines.append(f"- `{term}`: " + ", ".join(map(str, pages_found)))
    else:
        lines.append("- No direct card-system terms were found.")

    lines.extend(["", "## Core Rules Search Leads", ""])
    if rule_hits:
        for term, pages_found in rule_hits.items():
            lines.append(f"- `{term}`: " + ", ".join(map(str, pages_found)))
    else:
        lines.append("- No direct core-rule terms were found.")

    lines.extend(["", "## Extracted Pages", ""])
    for page_number in pages:
        row = connection.execute(
            """
            SELECT text,low_text,extraction_error
            FROM pages
            WHERE book_key=? AND page_number=?
            """,
            (COREBOOK_KEY, page_number),
        ).fetchone()
        if not row:
            continue
        text, low_text, error = row
        lines.extend([f"### PDF page {page_number}", ""])
        if error:
            lines.extend([f"**Extraction error:** `{error}`", ""])
        elif low_text or not str(text).strip():
            lines.extend(["**Low-text or image-heavy page.**", ""])
        else:
            lines.extend(["```text", str(text).strip(), "```", ""])

    path.write_text("\n".join(lines), encoding="utf-8")


def write_report(path: Path, refresh: dict[str, Any], deck_hits: dict[str, list[int]], rule_hits: dict[str, list[int]], backup: Path, built: str) -> None:
    path.write_text(
        "\n".join([
            "# FOXAI Necroscope Corebook OCR Refresh V1",
            "",
            f"- Completed: `{built}`",
            f"- OCR file: `{refresh['filename']}`",
            f"- OCR SHA-256: `{refresh['sha256']}`",
            f"- Pages indexed: **{refresh['page_count']}**",
            f"- Extracted characters: **{refresh['characters']:,}**",
            f"- Low-text pages: **{refresh['low_text_pages']}**",
            f"- Extraction-error pages: **{refresh['error_pages']}**",
            f"- FTS5 updated: **{refresh['fts_updated']}**",
            f"- Previous database backup: `{backup}`",
            "",
            "## Safety",
            "",
            "- The OCR PDF was opened read-only.",
            "- The original non-OCR corebook was not touched.",
            "- Only the `masterbook_core` rows were replaced.",
            "- The other five indexed books were not changed.",
            "- The database was updated on a temporary copy and replaced only after integrity verification.",
            "- No network access was used.",
            "",
            "## Results",
            "",
            f"- MasterDeck/card search terms found: **{len(deck_hits)}**",
            f"- Core-rule search terms found: **{len(rule_hits)}**",
            "",
            "The existing Campaign Room reads the SQLite index on every turn, so it can use the OCR corebook automatically.",
            "",
        ]),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "foxai.py").is_file():
        print("ERROR: FOXAI root not detected:", root)
        return 2

    source = root / "Library" / "DnD" / OCR_FILENAME
    if not source.is_file():
        print("ERROR: OCR corebook not found:", source)
        return 3

    index_dir = root / "Projects" / "NecroscopeCampaign" / "SourceIndexV1"
    database = index_dir / "necroscope_sources.sqlite3"
    if not database.is_file():
        print("ERROR: Existing source index missing:", database)
        return 4

    output_dir = root / "Projects" / "NecroscopeCampaign" / "CorebookOCRRefreshV1"
    output_dir.mkdir(parents=True, exist_ok=True)
    backup_dir = index_dir / "Backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    built = datetime.now().astimezone().isoformat(timespec="seconds")
    backup = backup_dir / f"necroscope_sources_before_corebook_ocr_{stamp}.sqlite3"
    temp_db = index_dir / f"necroscope_sources_corebook_refresh_{stamp}.building"

    shutil.copy2(database, backup)
    shutil.copy2(database, temp_db)

    try:
        with sqlite3.connect(str(temp_db)) as connection:
            validate_schema(connection)
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Existing database integrity check failed.")

            refresh = replace_corebook(connection, source, built)
            connection.commit()
            deck_hits = find_hits(connection, DECK_TERMS)
            rule_hits = find_hits(connection, RULE_TERMS)

            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Updated database integrity check failed.")

            packet = output_dir / "masterbook_corebook_ocr_rules_packet.md"
            write_packet(connection, packet, refresh, deck_hits, rule_hits, built)

        os.replace(temp_db, database)

        report = output_dir / "corebook_ocr_refresh_report.md"
        write_report(report, refresh, deck_hits, rule_hits, backup, built)

        manifest = {
            "schema": "foxai.necroscope.corebook_ocr_refresh.v1",
            "created": built,
            "network_used": False,
            "ocr_source_read_only": True,
            "database": str(database),
            "database_backup": str(backup),
            "ocr_source": str(source),
            "refresh": refresh,
            "deck_hits": deck_hits,
            "rule_hits": rule_hits,
            "packet": str(packet),
            "report": str(report),
        }
        manifest_path = output_dir / "corebook_ocr_refresh_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (output_dir / "LATEST.txt").write_text(
            f"{report}\n{packet}\n{manifest_path}\n{database}\n{backup}\n",
            encoding="utf-8",
        )

    except Exception as exc:
        temp_db.unlink(missing_ok=True)
        print("ERROR:", f"{type(exc).__name__}: {exc}")
        print("The live database was not replaced.")
        print("Backup preserved at:", backup)
        return 10

    print()
    print("=" * 72)
    print("NECROSCOPE COREBOOK OCR REFRESH COMPLETE")
    print("=" * 72)
    print("Pages indexed:", refresh["page_count"])
    print("Characters:", f"{refresh['characters']:,}")
    print("Low-text pages:", refresh["low_text_pages"])
    print("Extraction-error pages:", refresh["error_pages"])
    print("Deck terms found:", len(deck_hits))
    print("Database backup:", backup)
    print("Rules packet:", packet)
    print("Report:", report)
    print()
    print("The Campaign Room can now use the OCR corebook automatically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
