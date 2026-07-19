from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(r"Z:\FOXAI")
DATABASE = ROOT / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "Data" / "bibliotheca.sqlite3"
EXPECTED_REL_PATH = (
    "Recipes/PDF Collection/Cook-book-collection/"
    "(Book) - Cookbook - Nelson Family Recipe Book.pdf"
)

def main() -> int:
    if not DATABASE.is_file():
        print(json.dumps({
            "ok": False,
            "error": "Bibliotheca database not found.",
            "database": str(DATABASE),
        }, indent=2))
        return 1

    uri = DATABASE.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        document = connection.execute(
            """
            SELECT id,title,rel_path,text_status,is_ocr_copy,text_chars,page_count
            FROM documents
            WHERE rel_path=?
               OR LOWER(title)=LOWER(?)
            ORDER BY CASE WHEN rel_path=? THEN 0 ELSE 1 END,id
            LIMIT 1
            """,
            (
                EXPECTED_REL_PATH,
                "(Book) - Cookbook - Nelson Family Recipe Book",
                EXPECTED_REL_PATH,
            ),
        ).fetchone()

        if not document:
            print(json.dumps({
                "ok": False,
                "error": "Known-good Nelson Family Recipe Book record not found.",
                "expected_rel_path": EXPECTED_REL_PATH,
            }, indent=2))
            return 2

        page = connection.execute(
            """
            SELECT page_number,text,text_chars
            FROM pages
            WHERE document_id=? AND page_number=7
            """,
            (int(document["id"]),),
        ).fetchone()

        if not page:
            print(json.dumps({
                "ok": False,
                "error": "Page 7 record not found.",
                "document": dict(document),
            }, indent=2))
            return 3

        raw = str(page["text"] or "")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        relevant = [
            {
                "line_number": number,
                "text": line,
            }
            for number, line in enumerate(lines, start=1)
            if re.search(
                r"white\s*bread|bake|oven|degree|degrees|minute|minutes|"
                r"\b375\b|\b350\b|\b20\b|\b25\b|\b45\b",
                line,
                flags=re.IGNORECASE,
            )
        ]
        numeric_tokens = re.findall(r"\d+(?:[.,]\d+)?", raw)
        normalized = re.sub(r"\s+", " ", raw).strip()

        payload = {
            "ok": True,
            "read_only": True,
            "database": str(DATABASE),
            "document": dict(document),
            "page": {
                "page_number": int(page["page_number"]),
                "text_chars_database": int(page["text_chars"] or 0),
                "text_chars_actual": len(raw),
            },
            "numeric_tokens_in_order": numeric_tokens,
            "relevant_lines": relevant,
            "normalized_text": normalized,
            "raw_text_repr": repr(raw),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    finally:
        connection.close()

if __name__ == "__main__":
    raise SystemExit(main())
