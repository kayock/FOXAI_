from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
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

try:
    from pypdf import PdfReader
    import pypdf
except Exception as exc:
    print("ERROR: The bundled PDF extractor could not load.")
    print(f"{type(exc).__name__}: {exc}")
    raise SystemExit(8)


EXPECTED_BOOKS = [
    {
        "key": "masterbook_core",
        "title": "MasterBook Corebook",
        "filename": "Masterbook Corebook.pdf",
        "required": True,
    },
    {
        "key": "world_of_necroscope",
        "title": "MasterBook - World of Necroscope",
        "filename": "MasterBook - World of Necroscope.pdf",
        "required": True,
    },
    {
        "key": "e_branch_psionics",
        "title": "E-Branch Guide to Psionics",
        "filename": "MasterBook - World of Necroscope_ E-Branch Guide to Psionics.pdf",
        "required": False,
    },
    {
        "key": "operation_nightside",
        "title": "Operation Nightside",
        "filename": "[The World of Necroscope] - Operation Nightside.pdf",
        "required": False,
    },
    {
        "key": "wamphyri",
        "title": "Wamphyri",
        "filename": "MasterBook - World of Necroscope_ Wamphyri.pdf",
        "required": False,
    },
    {
        "key": "deadspeak_dossier",
        "title": "Deadspeak Dossier",
        "filename": "MasterBook - World of Necroscope_ Deadspeak Dossier.pdf",
        "required": False,
    },
]

SEARCH_GROUPS = {
    "Agent-Managed Deck": [
        "MasterDeck",
        "Master Deck",
        "action card",
        "subplot card",
        "cards in hand",
        "draw a card",
        "discard",
        "play a card",
        "card play",
        "hand limit",
        "deck",
    ],
    "Core Resolution": [
        "MasterBook Value Chart",
        "value chart",
        "result points",
        "difficulty number",
        "effect value",
        "2d10",
        "two ten-sided dice",
        "bonus number",
    ],
    "Character Creation": [
        "character creation",
        "attributes",
        "skills",
        "advantages",
        "disadvantages",
        "character points",
        "skill points",
    ],
    "Necroscope Lore": [
        "E-Branch",
        "deadspeak",
        "Wamphyri",
        "Necroscope",
        "psychic",
        "psionic",
        "vampire",
        "telepathy",
    ],
}


def normalize_name(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locate_books(library: Path) -> list[dict[str, Any]]:
    pdfs = [item for item in library.glob("*.pdf") if item.is_file()]
    exact = {item.name.casefold(): item for item in pdfs}
    normalized = {normalize_name(item.name): item for item in pdfs}

    found: list[dict[str, Any]] = []
    for expected in EXPECTED_BOOKS:
        path = exact.get(expected["filename"].casefold())
        if path is None:
            path = normalized.get(normalize_name(expected["filename"]))
        row = dict(expected)
        row["path"] = path
        found.append(row)
    return found


def clean_text(value: str) -> str:
    value = value.replace("\x00", "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{4,}", "\n\n\n", value)
    return value.strip()


def safe_extract_page(page: Any) -> tuple[str, str]:
    try:
        text = page.extract_text(extraction_mode="layout") or ""
        return clean_text(text), ""
    except TypeError:
        # Older/fallback API behavior.
        try:
            text = page.extract_text() or ""
            return clean_text(text), ""
        except Exception as exc:
            return "", f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        try:
            text = page.extract_text() or ""
            return clean_text(text), ""
        except Exception:
            return "", f"{type(exc).__name__}: {exc}"


def initialize_database(connection: sqlite3.Connection) -> bool:
    connection.executescript(
        """
        PRAGMA journal_mode=DELETE;
        PRAGMA synchronous=FULL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE books (
            book_key TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            source_path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            indexed_at TEXT NOT NULL
        );

        CREATE TABLE pages (
            page_id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_key TEXT NOT NULL,
            title TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            low_text INTEGER NOT NULL DEFAULT 0,
            extraction_error TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(book_key) REFERENCES books(book_key),
            UNIQUE(book_key, page_number)
        );

        CREATE INDEX idx_pages_book_page
            ON pages(book_key, page_number);
        CREATE INDEX idx_pages_low_text
            ON pages(low_text);
        """
    )

    fts_available = False
    try:
        connection.execute(
            """
            CREATE VIRTUAL TABLE pages_fts USING fts5(
                book_key UNINDEXED,
                title UNINDEXED,
                page_number UNINDEXED,
                text,
                tokenize='unicode61'
            )
            """
        )
        fts_available = True
    except sqlite3.OperationalError:
        fts_available = False

    return fts_available


def write_meta(
    connection: sqlite3.Connection,
    key: str,
    value: Any,
) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        (key, json.dumps(value, ensure_ascii=False)),
    )


def literal_hits(
    connection: sqlite3.Connection,
    term: str,
) -> list[tuple[str, str, int]]:
    rows = connection.execute(
        """
        SELECT book_key, title, page_number
        FROM pages
        WHERE instr(lower(text), lower(?)) > 0
        ORDER BY title, page_number
        """,
        (term,),
    ).fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def write_page_leads(
    connection: sqlite3.Connection,
    output_path: Path,
    indexed_at: str,
) -> None:
    lines = [
        "# Necroscope Page Leads V1",
        "",
        f"- Built: `{indexed_at}`",
        "- Sources: Eric's owned local MasterBook/Necroscope PDFs",
        "- Source handling: read-only",
        "- Page references are PDF page numbers reported by the extractor.",
        "",
    ]

    for group, terms in SEARCH_GROUPS.items():
        lines.extend([f"## {group}", ""])
        group_found = False

        for term in terms:
            rows = literal_hits(connection, term)
            if not rows:
                continue

            group_found = True
            by_book: dict[tuple[str, str], list[int]] = {}
            for key, title, page in rows:
                by_book.setdefault((key, title), []).append(page)

            lines.append(f"### `{term}`")
            lines.append("")
            for (_, title), pages in by_book.items():
                unique_pages = sorted(set(pages))
                shown = unique_pages[:40]
                page_text = ", ".join(str(page) for page in shown)
                if len(unique_pages) > len(shown):
                    page_text += f" ... (+{len(unique_pages) - len(shown)} more)"
                lines.append(f"- **{title}:** {page_text}")
            lines.append("")

        if not group_found:
            lines.extend(
                [
                    "No direct text matches were found in this group.",
                    "",
                ]
            )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_report(
    output_path: Path,
    *,
    indexed_at: str,
    db_path: Path,
    rows: list[dict[str, Any]],
    fts_available: bool,
    total_pages: int,
    total_characters: int,
    low_text_pages: int,
    error_pages: int,
) -> None:
    lines = [
        "# FOXAI Necroscope Portable PDF Index V1",
        "",
        f"- Built: `{indexed_at}`",
        f"- Database: `{db_path}`",
        f"- Extractor: **pypdf {pypdf.__version__} (isolated bundled copy)**",
        f"- Full-text search: **{'FTS5 enabled' if fts_available else 'SQLite LIKE fallback'}**",
        f"- Books indexed: **{len(rows)}**",
        f"- Pages indexed: **{total_pages:,}**",
        f"- Extracted characters: **{total_characters:,}**",
        f"- Low-text pages: **{low_text_pages:,}**",
        f"- Pages with extraction errors: **{error_pages:,}**",
        "",
        "## Safety",
        "",
        "- All source PDFs were opened read-only.",
        "- No source PDF was modified, renamed, moved, copied, or uploaded.",
        "- No network access was used.",
        "- The PDF extractor is isolated inside this package; FOXAI's main Python environment was not modified.",
        "- The database was built as a temporary file and replaced atomically only after success.",
        "",
        "## Indexed Books",
        "",
    ]

    for row in rows:
        lines.extend(
            [
                f"### {row['title']}",
                "",
                f"- File: `{row['filename']}`",
                f"- Pages: `{row['page_count']}`",
                f"- SHA-256: `{row['sha256']}`",
                f"- Extracted characters: `{row['characters']:,}`",
                f"- Low-text pages: `{row['low_text_pages']}`",
                f"- Extraction-error pages: `{row['error_pages']}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretation",
            "",
        ]
    )

    if error_pages:
        lines.append(
            "- Some pages could not be extracted. The index remains usable, but those pages may need selective OCR or screenshot review."
        )
    if low_text_pages:
        lines.append(
            "- Low-text pages are often covers, maps, illustrations, character sheets, or scanned-image pages. They are flagged for later visual review rather than guessed at."
        )
    if not error_pages and low_text_pages == 0:
        lines.append(
            "- Every indexed page produced substantial text. Direct page-grounded campaign work can proceed."
        )

    lines.extend(
        [
            "- The next development step is the Necroscope Campaign Room search service and Agent-Managed Deck rules extraction.",
            "",
            "## Quick Search",
            "",
            "Run:",
            "",
            "`SEARCH_NECROSCOPE_INDEX.bat`",
            "",
            "Useful first searches:",
            "",
            "- `MasterDeck`",
            "- `subplot card`",
            "- `result points`",
            "- `difficulty number`",
            "- `character creation`",
            "- `E-Branch`",
            "- `deadspeak`",
            "",
        ]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "foxai.py").is_file():
        print("ERROR: FOXAI root was not detected:", root)
        return 2

    library = root / "Library" / "DnD"
    if not library.is_dir():
        print("ERROR: Source library does not exist:", library)
        return 3

    located = locate_books(library)
    missing_required = [
        row["title"]
        for row in located
        if row["required"] and row["path"] is None
    ]
    if missing_required:
        print("ERROR: Required books are missing:")
        for title in missing_required:
            print("  -", title)
        return 4

    found = [row for row in located if row["path"] is not None]
    output_dir = root / "Projects" / "NecroscopeCampaign" / "SourceIndexV1"
    output_dir.mkdir(parents=True, exist_ok=True)

    db_path = output_dir / "necroscope_sources.sqlite3"
    temp_db = output_dir / "necroscope_sources.sqlite3.building"
    report_path = output_dir / "necroscope_index_report.md"
    leads_path = output_dir / "necroscope_page_leads.md"

    if temp_db.exists():
        temp_db.unlink()

    indexed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    indexed_books: list[dict[str, Any]] = []
    total_pages = 0
    total_characters = 0
    total_low_text = 0
    total_errors = 0

    print("=" * 70)
    print("FOXAI NECROSCOPE PORTABLE PDF INDEX V1")
    print("=" * 70)
    print("Bundled extractor:", f"pypdf {pypdf.__version__}")
    print("Source mode: READ-ONLY")
    print()

    with closing(sqlite3.connect(str(temp_db))) as connection:
        fts_available = initialize_database(connection)

        write_meta(connection, "schema", "foxai.necroscope.source_index.v1")
        write_meta(connection, "indexed_at", indexed_at)
        write_meta(connection, "read_only_sources", True)
        write_meta(connection, "network_used", False)
        write_meta(connection, "extractor", f"pypdf {pypdf.__version__}")
        write_meta(connection, "fts_available", fts_available)

        for book_number, item in enumerate(found, start=1):
            path: Path = item["path"]
            print(f"[{book_number}/{len(found)}] Opening read-only: {path.name}")

            try:
                reader = PdfReader(str(path), strict=False)
            except Exception as exc:
                print("ERROR: Could not open:", path)
                print(f"{type(exc).__name__}: {exc}")
                return 10

            if getattr(reader, "is_encrypted", False):
                try:
                    reader.decrypt("")
                except Exception:
                    print("ERROR: Encrypted PDF could not be opened:", path.name)
                    return 11

            file_hash = sha256_file(path)
            page_count = len(reader.pages)

            connection.execute(
                """
                INSERT INTO books(
                    book_key, title, filename, source_path,
                    size_bytes, sha256, page_count, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["key"],
                    item["title"],
                    path.name,
                    str(path),
                    path.stat().st_size,
                    file_hash,
                    page_count,
                    indexed_at,
                ),
            )

            book_chars = 0
            book_low = 0
            book_errors = 0

            for page_index, page in enumerate(reader.pages, start=1):
                text, error = safe_extract_page(page)
                char_count = len(text)
                low_text = 1 if len(re.sub(r"\s+", "", text)) < 80 else 0

                connection.execute(
                    """
                    INSERT INTO pages(
                        book_key, title, page_number, text,
                        char_count, low_text, extraction_error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["key"],
                        item["title"],
                        page_index,
                        text,
                        char_count,
                        low_text,
                        error,
                    ),
                )

                if fts_available:
                    connection.execute(
                        """
                        INSERT INTO pages_fts(
                            book_key, title, page_number, text
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            item["key"],
                            item["title"],
                            page_index,
                            text,
                        ),
                    )

                book_chars += char_count
                book_low += low_text
                book_errors += 1 if error else 0

                if page_index % 25 == 0 or page_index == page_count:
                    print(
                        f"    pages {page_index}/{page_count} | "
                        f"characters {book_chars:,} | low-text {book_low}"
                    )

            indexed_books.append(
                {
                    "key": item["key"],
                    "title": item["title"],
                    "filename": path.name,
                    "page_count": page_count,
                    "sha256": file_hash,
                    "characters": book_chars,
                    "low_text_pages": book_low,
                    "error_pages": book_errors,
                }
            )
            total_pages += page_count
            total_characters += book_chars
            total_low_text += book_low
            total_errors += book_errors
            connection.commit()

        write_meta(connection, "book_count", len(indexed_books))
        write_meta(connection, "page_count", total_pages)
        write_meta(connection, "character_count", total_characters)
        write_meta(connection, "low_text_pages", total_low_text)
        write_meta(connection, "error_pages", total_errors)
        connection.commit()

        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            print("ERROR: SQLite integrity check failed:", integrity)
            return 12

        write_page_leads(connection, leads_path, indexed_at)
        write_report(
            report_path,
            indexed_at=indexed_at,
            db_path=db_path,
            rows=indexed_books,
            fts_available=fts_available,
            total_pages=total_pages,
            total_characters=total_characters,
            low_text_pages=total_low_text,
            error_pages=total_errors,
        )

    if db_path.exists():
        backup = output_dir / (
            "necroscope_sources_"
            + datetime.now().strftime("%Y%m%dT%H%M%S")
            + ".sqlite3.backup"
        )
        shutil.copy2(db_path, backup)

    temp_db.replace(db_path)

    latest = output_dir / "LATEST.txt"
    latest.write_text(
        "\n".join(
            [
                str(report_path),
                str(leads_path),
                str(db_path),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("NECROSCOPE SOURCE INDEX COMPLETE")
    print("=" * 70)
    print("Books:", len(indexed_books))
    print("Pages:", f"{total_pages:,}")
    print("Characters:", f"{total_characters:,}")
    print("Low-text pages:", total_low_text)
    print("Extraction-error pages:", total_errors)
    print("Database:", db_path)
    print("Report:", report_path)
    print("Page leads:", leads_path)
    print()
    print("No source PDF was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
