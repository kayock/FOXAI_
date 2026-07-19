from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any


PACKETS = {
    "agent_managed_deck_rules": {
        "title": "Agent-Managed Deck Rules Packet",
        "purpose": (
            "Exact local page text needed to understand MasterDeck use, "
            "hands, drawing, discarding, subplot cards, and card effects."
        ),
        "queries": [
            ("MasterDeck", 12),
            ("Master Deck", 8),
            ("subplot card", 8),
            ("action card", 8),
            ("cards in hand", 8),
            ("draw a card", 8),
            ("discard", 10),
            ("play a card", 8),
            ("card play", 8),
            ("hand limit", 8),
        ],
        "seed_pages": [
            ("world_of_necroscope", 8),
            ("e_branch_psionics", 127),
            ("deadspeak_dossier", 27),
        ],
        "context": 1,
        "maximum_pages": 28,
    },
    "core_resolution_rules": {
        "title": "Core Resolution Rules Packet",
        "purpose": (
            "Page-cited rules for dice, the MasterBook Value Chart, "
            "difficulty numbers, result points, effect values, and bonuses."
        ),
        "queries": [
            ("MasterBook Value Chart", 10),
            ("value chart", 10),
            ("result points", 14),
            ("difficulty number", 14),
            ("effect value", 14),
            ("two ten-sided dice", 8),
            ("2d10", 8),
            ("bonus number", 8),
        ],
        "seed_pages": [
            ("world_of_necroscope", 25),
            ("world_of_necroscope", 26),
            ("world_of_necroscope", 27),
            ("world_of_necroscope", 31),
            ("world_of_necroscope", 32),
            ("deadspeak_dossier", 27),
        ],
        "context": 1,
        "maximum_pages": 42,
    },
    "character_creation_rules": {
        "title": "Character Creation Rules Packet",
        "purpose": (
            "Page-cited material for attributes, skills, advantages, "
            "disadvantages, character points, and campaign-ready creation."
        ),
        "queries": [
            ("character creation", 12),
            ("character points", 12),
            ("skill points", 12),
            ("attributes", 12),
            ("skills", 12),
            ("advantages", 12),
            ("disadvantages", 12),
        ],
        "seed_pages": [
            ("e_branch_psionics", 112),
            ("e_branch_psionics", 113),
            ("e_branch_psionics", 114),
            ("e_branch_psionics", 115),
            ("e_branch_psionics", 116),
            ("e_branch_psionics", 117),
            ("e_branch_psionics", 118),
            ("e_branch_psionics", 119),
            ("e_branch_psionics", 120),
            ("e_branch_psionics", 121),
            ("e_branch_psionics", 122),
            ("e_branch_psionics", 125),
            ("e_branch_psionics", 126),
            ("world_of_necroscope", 13),
            ("world_of_necroscope", 16),
            ("world_of_necroscope", 31),
            ("world_of_necroscope", 54),
        ],
        "context": 0,
        "maximum_pages": 44,
    },
    "campaign_lore_seed": {
        "title": "Necroscope Campaign Lore Seed",
        "purpose": (
            "A compact page-cited foundation for E-Branch, deadspeak, "
            "Wamphyri, psionics, telepathy, and the campaign's opening tone."
        ),
        "queries": [
            ("E-Branch", 8),
            ("deadspeak", 8),
            ("Wamphyri", 8),
            ("Necroscope", 6),
            ("psionic", 8),
            ("psychic", 8),
            ("telepathy", 8),
        ],
        "seed_pages": [
            ("world_of_necroscope", 4),
            ("world_of_necroscope", 5),
            ("world_of_necroscope", 6),
            ("world_of_necroscope", 7),
            ("world_of_necroscope", 8),
            ("e_branch_psionics", 4),
            ("e_branch_psionics", 5),
            ("deadspeak_dossier", 4),
            ("deadspeak_dossier", 5),
            ("wamphyri", 4),
            ("wamphyri", 5),
        ],
        "context": 0,
        "maximum_pages": 36,
    },
}


def database_path(root: Path) -> Path:
    return (
        root
        / "Projects"
        / "NecroscopeCampaign"
        / "SourceIndexV1"
        / "necroscope_sources.sqlite3"
    )


def packet_output_dir(root: Path) -> Path:
    return (
        root
        / "Projects"
        / "NecroscopeCampaign"
        / "RulesPacketsV1"
    )


def query_hits(
    connection: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[tuple[str, str, int]]:
    rows = connection.execute(
        """
        SELECT book_key, title, page_number
        FROM pages
        WHERE instr(lower(text), lower(?)) > 0
        ORDER BY
            CASE book_key
                WHEN 'world_of_necroscope' THEN 1
                WHEN 'e_branch_psionics' THEN 2
                WHEN 'deadspeak_dossier' THEN 3
                WHEN 'wamphyri' THEN 4
                WHEN 'operation_nightside' THEN 5
                ELSE 6
            END,
            page_number
        LIMIT ?
        """,
        (query, max(1, limit)),
    ).fetchall()
    return [(str(row[0]), str(row[1]), int(row[2])) for row in rows]


def book_page_counts(
    connection: sqlite3.Connection,
) -> dict[str, int]:
    return {
        str(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT book_key, page_count FROM books"
        ).fetchall()
    }


def expand_context(
    pages: set[tuple[str, int]],
    counts: dict[str, int],
    radius: int,
) -> set[tuple[str, int]]:
    expanded = set(pages)
    for book_key, page in list(pages):
        maximum = counts.get(book_key, page)
        for candidate in range(page - radius, page + radius + 1):
            if 1 <= candidate <= maximum:
                expanded.add((book_key, candidate))
    return expanded


def page_rows(
    connection: sqlite3.Connection,
    pages: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for book_key, page_number in sorted(pages):
        row = connection.execute(
            """
            SELECT
                p.book_key,
                p.title,
                p.page_number,
                p.text,
                p.char_count,
                p.low_text,
                p.extraction_error,
                b.filename,
                b.sha256
            FROM pages p
            JOIN books b ON b.book_key=p.book_key
            WHERE p.book_key=? AND p.page_number=?
            """,
            (book_key, page_number),
        ).fetchone()
        if not row:
            continue
        output.append(
            {
                "book_key": str(row[0]),
                "title": str(row[1]),
                "page_number": int(row[2]),
                "text": str(row[3] or ""),
                "char_count": int(row[4]),
                "low_text": bool(row[5]),
                "extraction_error": str(row[6] or ""),
                "filename": str(row[7]),
                "sha256": str(row[8]),
            }
        )
    return output


def select_packet_pages(
    connection: sqlite3.Connection,
    definition: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    selected: set[tuple[str, int]] = set(
        (str(book_key), int(page))
        for book_key, page in definition["seed_pages"]
    )
    hit_manifest: dict[str, list[dict[str, Any]]] = {}

    for query, limit in definition["queries"]:
        hits = query_hits(connection, query, limit)
        hit_manifest[query] = [
            {
                "book_key": book_key,
                "title": title,
                "page_number": page_number,
            }
            for book_key, title, page_number in hits
        ]
        selected.update(
            (book_key, page_number)
            for book_key, _, page_number in hits
        )

    selected = expand_context(
        selected,
        book_page_counts(connection),
        int(definition.get("context", 0)),
    )

    # Keep seeded pages, then add query/context pages in deterministic order.
    seed_set = set(
        (str(book_key), int(page))
        for book_key, page in definition["seed_pages"]
    )
    priority = sorted(seed_set)
    remainder = sorted(selected - seed_set)
    ordered = priority + remainder
    maximum = int(definition["maximum_pages"])
    chosen = set(ordered[:maximum])

    return page_rows(connection, chosen), hit_manifest


def clean_for_markdown(value: str) -> str:
    value = value.replace("\x00", "")
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"\n{5,}", "\n\n\n", value)
    return value.strip()


def write_packet(
    path: Path,
    definition: dict[str, Any],
    pages: list[dict[str, Any]],
    hits: dict[str, list[dict[str, Any]]],
    built: str,
) -> None:
    lines = [
        f"# {definition['title']}",
        "",
        f"- Built: `{built}`",
        "- Source: Eric's owned local MasterBook/Necroscope PDFs",
        "- Source handling: read-only",
        "- Page references below are PDF page numbers from the private source index.",
        f"- Purpose: {definition['purpose']}",
        "",
        "## Search Leads Used",
        "",
    ]

    for query, query_hits_list in hits.items():
        if not query_hits_list:
            lines.append(f"- `{query}`: no direct text hit")
            continue
        references = ", ".join(
            f"{item['title']} p. {item['page_number']}"
            for item in query_hits_list
        )
        lines.append(f"- `{query}`: {references}")

    lines.extend(["", "## Extracted Source Pages", ""])

    current_book = None
    for page in pages:
        if page["title"] != current_book:
            current_book = page["title"]
            lines.extend(
                [
                    f"## {current_book}",
                    "",
                    f"- File: `{page['filename']}`",
                    f"- Source SHA-256: `{page['sha256']}`",
                    "",
                ]
            )

        lines.extend(
            [
                f"### PDF page {page['page_number']}",
                "",
            ]
        )

        if page["extraction_error"]:
            lines.append(
                f"**Extraction error:** `{page['extraction_error']}`"
            )
            lines.append("")
        elif page["low_text"] or not page["text"].strip():
            lines.append(
                "**Low-text or image-heavy page.** This page may require "
                "visual review or selective OCR."
            )
            lines.append("")
        else:
            lines.extend(
                [
                    "```text",
                    clean_for_markdown(page["text"]),
                    "```",
                    "",
                ]
            )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_corebook_note(
    output_dir: Path,
    connection: sqlite3.Connection,
    built: str,
) -> None:
    row = connection.execute(
        """
        SELECT filename, page_count, sha256
        FROM books
        WHERE book_key='masterbook_core'
        """
    ).fetchone()

    lines = [
        "# MasterBook Corebook OCR Status",
        "",
        f"- Built: `{built}`",
        "",
    ]

    if not row:
        lines.extend(
            [
                "**Corebook record missing from the source index.**",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"- File: `{row[0]}`",
                f"- Pages: `{row[1]}`",
                f"- SHA-256: `{row[2]}`",
                "",
                "The corebook is present and intact, but all 180 pages are "
                "image-only in the current text index.",
                "",
                "The rules packets therefore use the extractable Necroscope "
                "books for immediate campaign preparation. The corebook should "
                "receive selective OCR only for rules that remain unclear after "
                "reviewing these packets.",
                "",
                "Do not OCR the entire book by default. Start with the smallest "
                "necessary page ranges identified during rules review.",
                "",
            ]
        )

    (output_dir / "masterbook_corebook_ocr_status.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "foxai.py").is_file():
        print("ERROR: FOXAI root was not detected:", root)
        return 2

    database = database_path(root)
    if not database.is_file():
        print("ERROR: Necroscope source database is missing:")
        print(database)
        print("Run the Portable PDF Index first.")
        return 3

    output_dir = packet_output_dir(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    built = datetime.now().astimezone().isoformat(timespec="seconds")

    manifest: dict[str, Any] = {
        "schema": "foxai.necroscope.rules_packets.v1",
        "built": built,
        "read_only_sources": True,
        "network_used": False,
        "source_database": str(database),
        "packets": {},
    }

    print("=" * 70)
    print("FOXAI NECROSCOPE RULES PACKET EXPORTER V1")
    print("=" * 70)
    print("Source database:", database)
    print("Source handling: READ-ONLY")
    print()

    with sqlite3.connect(str(database)) as connection:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()
        if not integrity or integrity[0] != "ok":
            print("ERROR: Source database integrity check failed.")
            return 4

        for packet_key, definition in PACKETS.items():
            print("Building:", definition["title"])
            pages, hits = select_packet_pages(
                connection,
                definition,
            )
            packet_path = output_dir / f"{packet_key}.md"
            write_packet(
                packet_path,
                definition,
                pages,
                hits,
                built,
            )
            manifest["packets"][packet_key] = {
                "title": definition["title"],
                "path": str(packet_path),
                "page_count": len(pages),
                "references": [
                    {
                        "book_key": page["book_key"],
                        "title": page["title"],
                        "page_number": page["page_number"],
                        "low_text": page["low_text"],
                    }
                    for page in pages
                ],
            }

        write_corebook_note(output_dir, connection, built)

    manifest_path = output_dir / "rules_packet_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    latest = output_dir / "LATEST.txt"
    latest.write_text(
        "\n".join(
            [
                str(output_dir / "agent_managed_deck_rules.md"),
                str(output_dir / "core_resolution_rules.md"),
                str(output_dir / "character_creation_rules.md"),
                str(output_dir / "campaign_lore_seed.md"),
                str(output_dir / "masterbook_corebook_ocr_status.md"),
                str(manifest_path),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 70)
    print("NECROSCOPE RULES PACKETS COMPLETE")
    print("=" * 70)
    print("Output:", output_dir)
    print()
    print("Upload these first:")
    print("  agent_managed_deck_rules.md")
    print("  core_resolution_rules.md")
    print("  character_creation_rules.md")
    print()
    print("No source PDF or source index was modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
