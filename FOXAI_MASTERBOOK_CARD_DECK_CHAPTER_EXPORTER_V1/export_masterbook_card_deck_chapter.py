from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
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
PAGE_START = 118
PAGE_END = 135

KEY_TERMS = [
    "Anatomy of a Card",
    "Anatomy of the Card Deck",
    "Number of Cards",
    "The Hand vs. The Pool",
    "Enhancement Cards",
    "Subplot Cards",
    "Picture Cards",
    "Cards in Combat and Interaction",
    "Determining Initiative",
    "Initiative Line Effects",
    "Approved Action Line",
    "Critical Skill Resolution",
    "Getting Cards",
    "Examples of Card Play",
    "MasterDeck",
    "discard",
    "draw",
    "hand",
    "pool",
]


def clean_text(value: str) -> str:
    value = value.replace("\x00", "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{4,}", "\n\n\n", value)
    return value.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def database_rows(database: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not database.is_file():
        return [], {"available": False, "reason": "database_missing"}

    with closing(sqlite3.connect(str(database))) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not {"books", "pages"}.issubset(tables):
            return [], {"available": False, "reason": "database_schema_missing"}

        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            return [], {"available": False, "reason": "database_integrity_failed"}

        book = connection.execute(
            """
            SELECT filename, source_path, sha256, page_count, indexed_at
            FROM books
            WHERE book_key=?
            """,
            (COREBOOK_KEY,),
        ).fetchone()
        if not book:
            return [], {"available": False, "reason": "corebook_record_missing"}

        rows = connection.execute(
            """
            SELECT page_number, text, char_count, low_text, extraction_error
            FROM pages
            WHERE book_key=?
              AND page_number BETWEEN ? AND ?
            ORDER BY page_number
            """,
            (COREBOOK_KEY, PAGE_START, PAGE_END),
        ).fetchall()

    output = [
        {
            "page_number": int(row[0]),
            "text": str(row[1] or ""),
            "char_count": int(row[2]),
            "low_text": bool(row[3]),
            "extraction_error": str(row[4] or ""),
        }
        for row in rows
    ]
    metadata = {
        "available": True,
        "reason": "ok",
        "filename": str(book[0]),
        "source_path": str(book[1]),
        "sha256": str(book[2]),
        "page_count": int(book[3]),
        "indexed_at": str(book[4]),
        "range_page_count": len(output),
        "range_characters": sum(item["char_count"] for item in output),
    }
    return output, metadata


def pdf_rows(pdf_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not pdf_path.is_file():
        return [], {"available": False, "reason": "ocr_pdf_missing"}

    reader = PdfReader(str(pdf_path), strict=False)
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception as exc:
            return [], {
                "available": False,
                "reason": f"ocr_pdf_encrypted: {type(exc).__name__}",
            }

    output = []
    for page_number in range(PAGE_START, PAGE_END + 1):
        if page_number < 1 or page_number > len(reader.pages):
            continue
        page = reader.pages[page_number - 1]
        error = ""
        try:
            try:
                text = page.extract_text(extraction_mode="layout") or ""
            except TypeError:
                text = page.extract_text() or ""
            text = clean_text(text)
        except Exception as exc:
            text = ""
            error = f"{type(exc).__name__}: {exc}"
        char_count = len(text)
        output.append(
            {
                "page_number": page_number,
                "text": text,
                "char_count": char_count,
                "low_text": len(re.sub(r"\s+", "", text)) < 80,
                "extraction_error": error,
            }
        )

    return output, {
        "available": True,
        "reason": "ok",
        "filename": pdf_path.name,
        "source_path": str(pdf_path),
        "sha256": sha256_file(pdf_path),
        "page_count": len(reader.pages),
        "range_page_count": len(output),
        "range_characters": sum(item["char_count"] for item in output),
        "extractor": f"pypdf {pypdf.__version__}",
    }


def useful_database(rows: list[dict[str, Any]]) -> bool:
    if len(rows) != (PAGE_END - PAGE_START + 1):
        return False
    total = sum(item["char_count"] for item in rows)
    meaningful = sum(1 for item in rows if item["char_count"] >= 120)
    return total >= 12000 and meaningful >= 12


def term_hits(rows: list[dict[str, Any]]) -> dict[str, list[int]]:
    output: dict[str, list[int]] = {}
    for term in KEY_TERMS:
        normalized_term = re.sub(r"\s+", "", term.casefold())
        hits = []
        for row in rows:
            normalized_text = re.sub(r"\s+", "", row["text"].casefold())
            if normalized_term in normalized_text:
                hits.append(row["page_number"])
        if hits:
            output[term] = hits
    return output


def write_packet(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    source_kind: str,
    source_meta: dict[str, Any],
    database_meta: dict[str, Any],
    hits: dict[str, list[int]],
    built: str,
) -> None:
    lines = [
        "# MasterBook Card Deck Chapter — Focused OCR Export",
        "",
        f"- Built: `{built}`",
        f"- Exported range: **PDF pages {PAGE_START}–{PAGE_END}**",
        f"- Text source used: **{source_kind}**",
        f"- Source file: `{source_meta.get('filename','unknown')}`",
        f"- Source SHA-256: `{source_meta.get('sha256','unknown')}`",
        f"- Pages exported: **{len(rows)}**",
        f"- Extracted characters in range: **{sum(row['char_count'] for row in rows):,}**",
        f"- Database corebook status: **{database_meta.get('reason','unknown')}**",
        "- Source handling: read-only",
        "",
        "## Live Database Verification",
        "",
    ]

    if useful_database(rows) and source_kind == "live SQLite database":
        lines.extend(
            [
                "**Verified:** the OCR corebook text is present in the live Necroscope source database.",
                "",
            ]
        )
    elif database_meta.get("available"):
        lines.extend(
            [
                "The database record exists, but the Card Deck range did not contain enough usable text. "
                "The exporter therefore used the OCR PDF directly.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "The live database could not supply the Card Deck range. "
                "The exporter used the OCR PDF directly so rules review can still continue.",
                "",
            ]
        )

    lines.extend(["## Located Headings and Terms", ""])
    if hits:
        for term, pages in hits.items():
            lines.append(f"- `{term}`: " + ", ".join(str(page) for page in pages))
    else:
        lines.append("- No exact normalized heading matches were found; review the exported pages below.")

    lines.extend(["", "## Card Deck Chapter Pages", ""])

    for row in rows:
        lines.extend([f"### PDF page {row['page_number']}", ""])
        if row["extraction_error"]:
            lines.extend([f"**Extraction error:** `{row['extraction_error']}`", ""])
        elif row["low_text"] or not row["text"].strip():
            lines.extend(["**Low-text or image-heavy page.**", ""])
        else:
            lines.extend(["```text", row["text"].strip(), "```", ""])

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "foxai.py").is_file():
        print("ERROR: FOXAI root was not detected:", root)
        return 2

    database = (
        root
        / "Projects"
        / "NecroscopeCampaign"
        / "SourceIndexV1"
        / "necroscope_sources.sqlite3"
    )
    ocr_pdf = root / "Library" / "DnD" / OCR_FILENAME

    db_rows, db_meta = database_rows(database)
    if useful_database(db_rows):
        rows = db_rows
        source_kind = "live SQLite database"
        source_meta = db_meta
    else:
        rows, pdf_meta = pdf_rows(ocr_pdf)
        if not rows:
            print("ERROR: Neither the live database nor OCR PDF supplied the Card Deck pages.")
            print("Database status:", db_meta.get("reason"))
            print("OCR PDF status:", pdf_meta.get("reason"))
            return 3
        source_kind = "OCR PDF fallback"
        source_meta = pdf_meta

    hits = term_hits(rows)
    built = datetime.now().astimezone().isoformat(timespec="seconds")
    output_dir = (
        root
        / "Projects"
        / "NecroscopeCampaign"
        / "CardDeckChapterV1"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    packet = output_dir / "masterbook_card_deck_chapter_pages_118_135.md"
    report = output_dir / "card_deck_chapter_export_report.json"

    write_packet(
        packet,
        rows,
        source_kind=source_kind,
        source_meta=source_meta,
        database_meta=db_meta,
        hits=hits,
        built=built,
    )

    payload = {
        "schema": "foxai.masterbook.card_deck_chapter_export.v1",
        "built": built,
        "read_only": True,
        "network_used": False,
        "page_start": PAGE_START,
        "page_end": PAGE_END,
        "source_kind": source_kind,
        "source_metadata": source_meta,
        "database_metadata": db_meta,
        "database_corebook_verified": (
            source_kind == "live SQLite database" and useful_database(rows)
        ),
        "term_hits": hits,
        "packet": str(packet),
    }
    report.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "LATEST.txt").write_text(
        f"{packet}\n{report}\n",
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("MASTERBOOK CARD DECK CHAPTER EXPORT COMPLETE")
    print("=" * 72)
    print("Source used:", source_kind)
    print("Database corebook verified:", payload["database_corebook_verified"])
    print("Pages:", len(rows))
    print("Characters:", f"{sum(row['char_count'] for row in rows):,}")
    print("Packet:", packet)
    print("Report:", report)
    print()
    print("No PDF or database was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
