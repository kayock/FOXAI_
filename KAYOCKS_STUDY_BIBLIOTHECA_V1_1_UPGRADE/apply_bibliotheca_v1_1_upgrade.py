from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import py_compile
import shutil
import sqlite3
import tempfile


SOURCE_SHA256 = "5c99722f7131f41926db74a6641f0a05b7137fd401fa2dedafa43f3c24844215"
PATCHED_SHA256 = "d11260cd703d3abd40888fe62769b78ec833a67446f6528f5e414f8837ca85d5"
PATCH_ID = "foxai.kayocks_study.bibliotheca.v1.1"

REQUIRED_MARKERS = (
    'APP_VERSION = "1.1"',
    'def duplicate_groups(',
    'def move_duplicate_candidates(',
    'def shelf_for_rel_path(',
    '"/api/index/pause"',
    '"/api/index/cancel"',
    '"/api/cleanup/move"',
    'Bibliotheca V1.1',
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compile_file(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="bibliotheca_v1_1_") as temp:
        py_compile.compile(
            str(path),
            cfile=str(Path(temp) / "study_server.pyc"),
            doraise=True,
        )


def database_counts(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False, "documents": 0, "pages": 0, "size_bytes": 0}
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    try:
        documents = conn.execute(
            "SELECT COUNT(*) FROM documents"
        ).fetchone()[0]
        pages = conn.execute(
            "SELECT COUNT(*) FROM pages"
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        "exists": True,
        "documents": int(documents),
        "pages": int(pages),
        "size_bytes": path.stat().st_size,
    }


def snapshot_database(source: Path, destination: Path) -> dict:
    if not source.is_file():
        return {"created": False, "reason": "database_not_present"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_uri = source.resolve().as_uri() + "?mode=ro"
    src = sqlite3.connect(source_uri, uri=True, timeout=30)
    dst = sqlite3.connect(str(destination))
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close()
        src.close()
    source_counts = database_counts(source)
    backup_counts = database_counts(destination)
    if (
        source_counts["documents"] != backup_counts["documents"]
        or source_counts["pages"] != backup_counts["pages"]
    ):
        raise RuntimeError("Database snapshot count verification failed.")
    return {
        "created": True,
        "path": str(destination),
        "source_counts": source_counts,
        "backup_counts": backup_counts,
        "sha256": sha256_file(destination),
    }


def write_receipt(root: Path, action: str, details: dict) -> Path:
    folder = root / "Reports" / "KayocksStudy" / "Bibliotheca" / "V1_1Upgrade"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    path = folder / f"{stamp}_{action}_receipt.json"
    path.write_text(
        json.dumps(
            {
                "schema": "foxai.patch.receipt.v1",
                "patch_id": PATCH_ID,
                "action": action,
                "created": datetime.now().astimezone().isoformat(
                    timespec="seconds"
                ),
                "verified": True,
                "network_used": False,
                "details": details,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def apply(root: Path, package: Path) -> int:
    app_dir = root / "KAYOCKS_STUDY_BIBLIOTHECA_V1"
    target = app_dir / "study_server.py"
    payload = package / "payload" / "study_server.py"
    database = app_dir / "Data" / "bibliotheca.sqlite3"

    if not (root / "Library").is_dir():
        print("ERROR: FOXAI Library was not found:", root / "Library")
        return 2
    if not target.is_file():
        print("ERROR: Bibliotheca V1 server was not found:", target)
        return 3
    if not payload.is_file():
        print("ERROR: V1.1 payload is missing:", payload)
        return 4

    payload_hash = sha256_file(payload)
    if payload_hash != PATCHED_SHA256:
        print("ERROR: V1.1 payload verification failed.")
        print("Expected:", PATCHED_SHA256)
        print("Actual:  ", payload_hash)
        return 5

    payload_text = payload.read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_MARKERS if marker not in payload_text]
    if missing:
        print("ERROR: Required V1.1 markers are missing:", ", ".join(missing))
        return 6
    compile_file(payload)

    live_hash = sha256_file(target)
    if live_hash == PATCHED_SHA256:
        print("Bibliotheca V1.1 is already installed.")
        print("Database:", database_counts(database))
        return 0
    if live_hash != SOURCE_SHA256:
        print("ERROR: Live Study server does not match the reviewed V1 build.")
        print("Nothing was changed.")
        print("Expected:", SOURCE_SHA256)
        print("Actual:  ", live_hash)
        return 7

    before_db = database_counts(database)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir = (
        root / "Backups" / "KayocksStudy" / "BibliothecaV1_1" / stamp
    )
    backup_dir.mkdir(parents=True, exist_ok=False)

    server_backup = backup_dir / "study_server_v1.py"
    shutil.copy2(target, server_backup)
    if sha256_file(server_backup) != SOURCE_SHA256:
        print("ERROR: V1 server backup verification failed.")
        return 8

    database_snapshot = snapshot_database(
        database,
        backup_dir / "bibliotheca_before_v1_1.sqlite3",
    )

    temporary = target.with_name("study_server.py.v1_1.tmp")
    shutil.copy2(payload, temporary)

    try:
        compile_file(temporary)
        if sha256_file(temporary) != PATCHED_SHA256:
            raise RuntimeError("Temporary V1.1 verification failed.")
        os.replace(temporary, target)
        if sha256_file(target) != PATCHED_SHA256:
            raise RuntimeError("Post-install server verification failed.")
        after_db = database_counts(database)
        if before_db != after_db:
            raise RuntimeError("Live Bibliotheca database changed during upgrade.")
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        shutil.copy2(server_backup, target)
        print("ERROR:", exc)
        print("The verified V1 server was restored.")
        return 9

    target_readme = app_dir / "README_V1_1.txt"
    target_readme.write_text(
        (package / "README_FIRST.txt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    receipt = write_receipt(
        root,
        "apply",
        {
            "target": str(target),
            "before_sha256": SOURCE_SHA256,
            "after_sha256": PATCHED_SHA256,
            "server_backup": str(server_backup),
            "database_before": before_db,
            "database_after": database_counts(database),
            "database_snapshot": database_snapshot,
            "database_preserved": True,
            "source_files_modified": 1,
            "source_files_added": 1,
            "source_files_deleted": 0,
            "original_pdfs_modified": 0,
            "original_pdfs_deleted": 0,
            "features": [
                "collection shelves",
                "Recipes shelf",
                "shelf and text-status filters",
                "duplicate review",
                "preview-first move to Needs Review",
                "pause and resume indexing",
                "stop after current PDF",
                "fast incremental unchanged-file skip",
            ],
        },
    )

    print()
    print("=" * 72)
    print("KAYOCK'S STUDY — BIBLIOTHECA V1.1 INSTALLED")
    print("=" * 72)
    print("Server:", target)
    print("SHA-256:", PATCHED_SHA256)
    print("Database preserved:", database_counts(database))
    print("Backup:", backup_dir)
    print("Receipt:", receipt)
    print()
    print("Restart START_KAYOCKS_STUDY.bat.")
    return 0


def rollback(root: Path) -> int:
    target = (
        root / "KAYOCKS_STUDY_BIBLIOTHECA_V1" / "study_server.py"
    )
    backup_base = root / "Backups" / "KayocksStudy" / "BibliothecaV1_1"

    if not target.is_file():
        print("ERROR: Bibliotheca server is missing:", target)
        return 20

    live_hash = sha256_file(target)
    if live_hash == SOURCE_SHA256:
        print("Bibliotheca V1 is already active.")
        return 0
    if live_hash != PATCHED_SHA256:
        print("ERROR: Study server changed after V1.1.")
        print("Rollback stopped to protect newer work.")
        return 21

    backups = sorted(
        (
            item for item in backup_base.glob("*/study_server_v1.py")
            if item.is_file() and sha256_file(item) == SOURCE_SHA256
        ),
        key=lambda item: item.parent.name,
        reverse=True,
    )
    if not backups:
        print("ERROR: No verified V1 server backup was found.")
        return 22

    backup = backups[0]
    preserve_dir = (
        root
        / "Backups"
        / "KayocksStudy"
        / "BibliothecaV1_1Rollback"
        / datetime.now().strftime("%Y%m%dT%H%M%S")
    )
    preserve_dir.mkdir(parents=True, exist_ok=False)
    v11_copy = preserve_dir / "study_server_v1_1.py"
    shutil.copy2(target, v11_copy)

    temporary = target.with_name("study_server.py.rollback.tmp")
    shutil.copy2(backup, temporary)
    try:
        if sha256_file(temporary) != SOURCE_SHA256:
            raise RuntimeError("Rollback source verification failed.")
        os.replace(temporary, target)
        if sha256_file(target) != SOURCE_SHA256:
            raise RuntimeError("Rollback post-write verification failed.")
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        shutil.copy2(v11_copy, target)
        print("ERROR:", exc)
        print("The V1.1 server was restored.")
        return 23

    receipt = write_receipt(
        root,
        "rollback",
        {
            "target": str(target),
            "restored_sha256": SOURCE_SHA256,
            "restored_from": str(backup),
            "v1_1_preserved": str(v11_copy),
            "database_changed": False,
        },
    )
    print("Bibliotheca V1.1 was rolled back to V1.")
    print("Database was not changed.")
    print("Receipt:", receipt)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument(
        "--action",
        choices=("apply", "rollback"),
        default="apply",
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    package = Path(__file__).resolve().parent
    return rollback(root) if args.action == "rollback" else apply(root, package)


if __name__ == "__main__":
    raise SystemExit(main())
