from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sqlite3
import sys


def snippet_text(text: str, query: str, radius: int = 260) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if not compact:
        return "[No extractable text on this page]"

    position = compact.casefold().find(query.casefold())
    if position < 0:
        return compact[: radius * 2] + ("..." if len(compact) > radius * 2 else "")

    start = max(0, position - radius)
    end = min(len(compact), position + len(query) + radius)
    prefix = "..." if start else ""
    suffix = "..." if end < len(compact) else ""
    return prefix + compact[start:end] + suffix


def has_fts(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT value FROM meta WHERE key='fts_available'"
    ).fetchone()
    if not row:
        return False
    try:
        return bool(json.loads(row[0]))
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--book", default="")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    db = (
        root
        / "Projects"
        / "NecroscopeCampaign"
        / "SourceIndexV1"
        / "necroscope_sources.sqlite3"
    )
    if not db.is_file():
        print("ERROR: The Necroscope source index has not been built yet.")
        print("Run RUN_NECROSCOPE_PDF_INDEX.bat first.")
        return 2

    query = args.query.strip()
    if not query:
        print("ERROR: Search query is empty.")
        return 3

    with sqlite3.connect(str(db)) as connection:
        rows = []

        # Literal search is reliable for rule phrases and avoids FTS syntax issues.
        sql = """
            SELECT book_key, title, page_number, text
            FROM pages
            WHERE instr(lower(text), lower(?)) > 0
        """
        params: list[object] = [query]
        if args.book.strip():
            sql += " AND lower(book_key)=lower(?)"
            params.append(args.book.strip())
        sql += " ORDER BY title, page_number LIMIT ?"
        params.append(max(1, min(args.limit, 100)))
        rows = connection.execute(sql, params).fetchall()

        if not rows and has_fts(connection):
            try:
                fts_sql = """
                    SELECT book_key, title, page_number, text
                    FROM pages_fts
                    WHERE pages_fts MATCH ?
                """
                fts_params: list[object] = [query]
                if args.book.strip():
                    fts_sql += " AND lower(book_key)=lower(?)"
                    fts_params.append(args.book.strip())
                fts_sql += " LIMIT ?"
                fts_params.append(max(1, min(args.limit, 100)))
                rows = connection.execute(fts_sql, fts_params).fetchall()
            except sqlite3.OperationalError:
                rows = []

    print()
    print("=" * 70)
    print("NECROSCOPE SOURCE SEARCH")
    print("=" * 70)
    print("Query:", query)
    print("Results:", len(rows))
    print()

    if not rows:
        print("No indexed page contained that phrase.")
        return 0

    for index, (book_key, title, page_number, text) in enumerate(rows, start=1):
        print(f"[{index}] {title} - PDF page {page_number}")
        print(f"    Book key: {book_key}")
        print("    " + snippet_text(text, query))
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
