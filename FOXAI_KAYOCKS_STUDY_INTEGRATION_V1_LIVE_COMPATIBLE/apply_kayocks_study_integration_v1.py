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


SOURCE_SHA256="5601b36cd49d213d367954b9ff5e1456fb3c41b5eabe0b7e1ba56364e8ecec65"
PATCHED_SHA256="e1ae59bddc87a3f624939f5935b17da9d36d972e09e21aaebaeb2c2108d04ee2"
PATCH_ID="foxai.kayocks_study.integration.v1"


def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def compile_file(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="foxai_study_v1_") as temp:
        py_compile.compile(
            str(path),
            cfile=str(Path(temp)/"foxai_web.pyc"),
            doraise=True,
        )


def database_counts(path: Path) -> dict:
    if not path.is_file():
        return {"exists":False,"documents":0,"pages":0}
    uri=path.resolve().as_uri()+"?mode=ro"
    connection=sqlite3.connect(uri,uri=True,timeout=15)
    try:
        documents=connection.execute(
            "SELECT COUNT(*) FROM documents"
        ).fetchone()[0]
        pages=connection.execute(
            "SELECT COUNT(*) FROM pages"
        ).fetchone()[0]
    finally:
        connection.close()
    return {
        "exists":True,
        "documents":int(documents),
        "pages":int(pages),
    }


def snapshot_database(source: Path,destination: Path) -> dict:
    if not source.is_file():
        return {"created":False,"reason":"database_not_present"}
    destination.parent.mkdir(parents=True,exist_ok=True)
    source_uri=source.resolve().as_uri()+"?mode=ro"
    source_connection=sqlite3.connect(
        source_uri,
        uri=True,
        timeout=30,
    )
    destination_connection=sqlite3.connect(str(destination))
    try:
        source_connection.backup(destination_connection)
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()
    before=database_counts(source)
    after=database_counts(destination)
    if before!=after:
        raise RuntimeError("Bibliotheca database snapshot verification failed.")
    return {
        "created":True,
        "path":str(destination),
        "counts":after,
        "sha256":sha256_file(destination),
    }


def write_receipt(root: Path,action: str,details: dict) -> Path:
    folder=root/"Reports"/"KayocksStudy"/"MainFOXAIIntegration"
    folder.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime("%Y%m%dT%H%M%S")
    path=folder/f"{stamp}_{action}_receipt.json"
    path.write_text(
        json.dumps(
            {
                "schema":"foxai.patch.receipt.v1",
                "patch_id":PATCH_ID,
                "action":action,
                "created":datetime.now().astimezone().isoformat(
                    timespec="seconds"
                ),
                "verified":True,
                "network_used":False,
                "details":details,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def apply(root: Path,package: Path) -> int:
    target=root/"core"/"foxai_web.py"
    payload=package/"payload"/"foxai_web.py"
    study_server=(
        root/"KAYOCKS_STUDY_BIBLIOTHECA_V1"/"study_server.py"
    )
    database=(
        root/"KAYOCKS_STUDY_BIBLIOTHECA_V1"
        /"Data"/"bibliotheca.sqlite3"
    )

    if not target.is_file():
        print("ERROR: Live FOXAI WebUI was not found:",target)
        return 2
    if not payload.is_file():
        print("ERROR: Integration payload is missing:",payload)
        return 3
    if not study_server.is_file():
        print("ERROR: Kayock's Study server was not found:",study_server)
        print("Nothing was changed.")
        return 4
    if sha256_file(payload)!=PATCHED_SHA256:
        print("ERROR: Integration payload verification failed.")
        return 5

    compile_file(payload)
    live_hash=sha256_file(target)
    if live_hash==PATCHED_SHA256:
        print("Kayock's Study Integration V1 is already installed.")
        print("Bibliotheca database:",database_counts(database))
        return 0
    if live_hash!=SOURCE_SHA256:
        print("ERROR: Live foxai_web.py does not match the reviewed build.")
        print("Nothing was changed.")
        print("Expected:",SOURCE_SHA256)
        print("Actual:  ",live_hash)
        return 6

    before_database=database_counts(database)
    stamp=datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_dir=(
        root/"Backups"/"KayocksStudy"/"MainFOXAIIntegration"/stamp
    )
    backup_dir.mkdir(parents=True,exist_ok=False)

    webui_backup=backup_dir/"foxai_web_before_study_integration.py"
    shutil.copy2(target,webui_backup)
    if sha256_file(webui_backup)!=SOURCE_SHA256:
        print("ERROR: WebUI backup verification failed.")
        return 7

    database_snapshot=snapshot_database(
        database,
        backup_dir/"bibliotheca_before_main_integration.sqlite3",
    )

    temporary=target.with_name("foxai_web.py.study_v1.tmp")
    shutil.copy2(payload,temporary)
    try:
        compile_file(temporary)
        if sha256_file(temporary)!=PATCHED_SHA256:
            raise RuntimeError("Temporary integration verification failed.")
        os.replace(temporary,target)
        if sha256_file(target)!=PATCHED_SHA256:
            raise RuntimeError("Post-install WebUI verification failed.")
        after_database=database_counts(database)
        if before_database!=after_database:
            raise RuntimeError(
                "Bibliotheca database counts changed during integration."
            )
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        shutil.copy2(webui_backup,target)
        print("ERROR:",exc)
        print("The verified original WebUI was restored.")
        return 8

    receipt=write_receipt(
        root,
        "apply",
        {
            "target":str(target),
            "before_sha256":SOURCE_SHA256,
            "after_sha256":PATCHED_SHA256,
            "webui_backup":str(webui_backup),
            "bibliotheca_database_before":before_database,
            "bibliotheca_database_after":database_counts(database),
            "bibliotheca_database_snapshot":database_snapshot,
            "database_preserved":True,
            "original_pdfs_modified":0,
            "original_pdfs_deleted":0,
            "navigation_groups_modified":False,
            "writer_modified":False,
            "repair_bay_modified":False,
            "standalone_study_modified":False,
            "features":[
                "Iron Library sidebar label renamed to Kayock's Study",
                "Study starts only when its FOXAI page is entered",
                "live Bibliotheca status and collection totals",
                "embedded Bibliotheca workspace",
                "full standalone Study button",
                "legacy file browser preserved in a foldout",
            ],
        },
    )

    print()
    print("="*72)
    print("KAYOCK'S STUDY INTEGRATION V1 INSTALLED")
    print("="*72)
    print("WebUI:",target)
    print("SHA-256:",PATCHED_SHA256)
    print("Bibliotheca database preserved:",database_counts(database))
    print("Backup:",backup_dir)
    print("Receipt:",receipt)
    print()
    print("Restart the FOXAI WebUI once to load the new page.")
    return 0


def rollback(root: Path) -> int:
    target=root/"core"/"foxai_web.py"
    backup_base=(
        root/"Backups"/"KayocksStudy"/"MainFOXAIIntegration"
    )

    if not target.is_file():
        print("ERROR: Live FOXAI WebUI is missing:",target)
        return 20

    live_hash=sha256_file(target)
    if live_hash==SOURCE_SHA256:
        print("The original FOXAI WebUI is already active.")
        return 0
    if live_hash!=PATCHED_SHA256:
        print("ERROR: FOXAI WebUI changed after this integration.")
        print("Rollback stopped to protect newer work.")
        return 21

    backups=sorted(
        (
            path
            for path in backup_base.glob(
                "*/foxai_web_before_study_integration.py"
            )
            if path.is_file()
            and sha256_file(path)==SOURCE_SHA256
        ),
        key=lambda path:path.parent.name,
        reverse=True,
    )
    if not backups:
        print("ERROR: No verified pre-integration WebUI backup was found.")
        return 22

    backup=backups[0]
    preserve_dir=(
        root/"Backups"/"KayocksStudy"
        /"MainFOXAIIntegrationRollback"
        /datetime.now().strftime("%Y%m%dT%H%M%S")
    )
    preserve_dir.mkdir(parents=True,exist_ok=False)
    integrated_copy=preserve_dir/"foxai_web_study_integration_v1.py"
    shutil.copy2(target,integrated_copy)

    temporary=target.with_name("foxai_web.py.rollback.tmp")
    shutil.copy2(backup,temporary)
    try:
        compile_file(temporary)
        if sha256_file(temporary)!=SOURCE_SHA256:
            raise RuntimeError("Rollback source verification failed.")
        os.replace(temporary,target)
        if sha256_file(target)!=SOURCE_SHA256:
            raise RuntimeError("Rollback post-write verification failed.")
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        shutil.copy2(integrated_copy,target)
        print("ERROR:",exc)
        print("The integrated WebUI was restored.")
        return 23

    receipt=write_receipt(
        root,
        "rollback",
        {
            "target":str(target),
            "restored_sha256":SOURCE_SHA256,
            "restored_from":str(backup),
            "integrated_copy_preserved":str(integrated_copy),
            "bibliotheca_database_changed":False,
            "standalone_study_changed":False,
        },
    )
    print("Kayock's Study Integration V1 was rolled back.")
    print("The Bibliotheca database and standalone Study were untouched.")
    print("Receipt:",receipt)
    return 0


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",required=True)
    parser.add_argument(
        "--action",
        choices=("apply","rollback"),
        default="apply",
    )
    args=parser.parse_args()
    root=Path(args.root).resolve()
    package=Path(__file__).resolve().parent
    return (
        rollback(root)
        if args.action=="rollback"
        else apply(root,package)
    )


if __name__=="__main__":
    raise SystemExit(main())
