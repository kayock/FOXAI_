from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

EXPECTED_POINTER = Path("System/Portability/COMFYUI_KNOWN_GOOD_CURRENT.json")


def sha256_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def baseline_tree(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    for item in sorted(path.rglob("*"), key=lambda p: p.relative_to(path).as_posix().casefold()):
        if item.is_symlink():
            issues.append(f"symlink not allowed: {item}")
            continue
        if not item.is_file():
            continue
        rel = item.relative_to(path).as_posix()
        rows.append({"path": rel, "size_bytes": item.stat().st_size, "sha256": sha256_file(item)})
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["path"].casefold().encode("utf-8", errors="surrogatepass"))
        digest.update(b"\0")
        digest.update(str(row["size_bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(row["sha256"].encode("ascii"))
        digest.update(b"\n")
    return {"verified": not issues, "file_count": len(rows), "tree_sha256": digest.hexdigest(), "issues": issues}


def verify_rows(root: Path, rows: list[dict[str, Any]], label: str, progress: bool = False) -> dict[str, Any]:
    missing: list[str] = []
    mismatches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        rel = str(row["relative_path"] if "relative_path" in row else row["path"]).replace("\\", "/")
        key = rel.casefold()
        if key in seen:
            raise RuntimeError(f"duplicate case-insensitive {label} path: {rel}")
        seen.add(key)
        path = root / Path(rel)
        if not path.is_file() or path.is_symlink():
            missing.append(rel)
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        if size != int(row["size_bytes"]) or digest != row["sha256"]:
            mismatches.append({"path": rel, "size_bytes": size, "sha256": digest})
        if progress and index % 1000 == 0:
            print(f"  verified {index:,}/{len(rows):,} files", flush=True)
    return {"verified": not missing and not mismatches, "missing": missing, "mismatches": mismatches}


def verify_target(root: Path, baseline: Path, quick: bool) -> dict[str, Any]:
    manifest = read_json(baseline / "ISOLATED_TARGET_MANIFEST.json")
    rows = manifest["files"]
    target = root / Path(manifest["relative_path"])
    if quick:
        return {"verified": target.is_dir(), "quick": True, "target": str(target)}
    result = verify_rows(target, rows, "target", progress=True)
    target_entries = list(target.rglob("*"))
    actual_files = {
        p.relative_to(target).as_posix().casefold()
        for p in target_entries
        if p.is_file() and not p.is_symlink()
    }
    symlinks = sorted(
        p.relative_to(target).as_posix() for p in target_entries if p.is_symlink()
    )
    expected_files = {str(row["path"]).casefold() for row in rows}
    unexpected = sorted(actual_files - expected_files)
    result["unexpected"] = unexpected
    result["symlinks"] = symlinks
    result["verified"] = bool(result["verified"] and not unexpected and not symlinks)
    if result["verified"]:
        digest = hashlib.sha256()
        total = 0
        for row in rows:
            digest.update(str(row["path"]).casefold().encode("utf-8", errors="surrogatepass"))
            digest.update(b"\0")
            digest.update(str(row["size_bytes"]).encode("ascii"))
            digest.update(b"\0")
            digest.update(str(row["sha256"]).encode("ascii"))
            digest.update(b"\n")
            total += int(row["size_bytes"])
        result.update({"file_count": len(rows), "total_bytes": total, "tree_sha256": digest.hexdigest()})
        result["verified"] = (
            result["file_count"] == manifest["file_count"]
            and result["total_bytes"] == manifest["total_bytes"]
            and result["tree_sha256"] == manifest["tree_sha256"]
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the sealed FOXAI ComfyUI known-good baseline.")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--quick", action="store_true", help="Verify baseline metadata and critical live files without rehashing all 39,046 runtime files.")
    args = parser.parse_args()
    script = Path(__file__).resolve()
    root = args.root.resolve() if args.root else script.parents[2]
    pointer_path = root / EXPECTED_POINTER
    if not pointer_path.is_file():
        print(f"[FAILED] Baseline pointer is missing: {pointer_path}")
        return 19
    pointer = read_json(pointer_path)
    baseline = root / Path(pointer["baseline_relative_path"])
    if not baseline.is_dir() or baseline.is_symlink():
        print(f"[FAILED] Baseline directory is missing or unsafe: {baseline}")
        return 19
    tree = baseline_tree(baseline)
    if not tree["verified"] or tree["file_count"] != pointer["baseline_file_count"] or tree["tree_sha256"] != pointer["baseline_tree_sha256"]:
        print("[FAILED] Baseline metadata tree does not match the sealed pointer.")
        return 19
    seal = read_json(baseline / "BASELINE_SEAL.json")
    if seal.get("classification") != "C3L_PORTABILITY_CLOSED_KNOWN_GOOD_BASELINE_SEALED":
        print("[FAILED] Baseline seal classification is invalid.")
        return 19
    critical = read_json(baseline / "INTEGRATED_FILES_MANIFEST.json")["files"]
    protected = read_json(baseline / "PROTECTED_FILES_MANIFEST.json")["files"]
    critical_result = verify_rows(root, critical, "integrated")
    protected_result = verify_rows(root, protected, "protected")
    if not critical_result["verified"] or not protected_result["verified"]:
        print("[FAILED] One or more critical live files differ from the known-good baseline.")
        return 19
    target_result = verify_target(root, baseline, args.quick)
    if not target_result["verified"]:
        print("[FAILED] The isolated dependency target differs from the known-good baseline.")
        return 19
    print("[VERIFIED] FOXAI ComfyUI matches the sealed known-good baseline.")
    print(f"Baseline: {pointer['baseline_id']}")
    print(f"Mode: {'quick' if args.quick else 'full 39,046-file verification'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
