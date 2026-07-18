from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

POINTER = Path("System/Portability/COMFYUI_KNOWN_GOOD_CURRENT.json")
ALLOWED_CLASSIFICATIONS = {
    "C3L_PORTABILITY_CLOSED_KNOWN_GOOD_BASELINE_SEALED",
    "C4F_DUAL_PROFILE_KNOWN_GOOD_BASELINE_SEALED_C4_CLOSED",
}


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
    for item in sorted(
        path.rglob("*"),
        key=lambda p: p.relative_to(path).as_posix().casefold(),
    ):
        if item.is_symlink():
            issues.append(f"symlink not allowed: {item}")
            continue
        if not item.is_file():
            continue
        rel = item.relative_to(path).as_posix()
        rows.append(
            {
                "path": rel,
                "size_bytes": item.stat().st_size,
                "sha256": sha256_file(item),
            }
        )
    aggregate = hashlib.sha256()
    for row in rows:
        aggregate.update(row["path"].casefold().encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(row["size_bytes"]).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(row["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    return {
        "verified": not issues,
        "file_count": len(rows),
        "tree_sha256": aggregate.hexdigest(),
        "issues": issues,
    }


def verify_rows(
    root: Path,
    rows: list[dict[str, Any]],
    label: str,
    progress: bool = False,
) -> dict[str, Any]:
    missing: list[str] = []
    mismatches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        rel = str(
            row["relative_path"] if "relative_path" in row else row["path"]
        ).replace("\\", "/")
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
            mismatches.append(
                {"path": rel, "size_bytes": size, "sha256": digest}
            )
        if progress and index % 1000 == 0:
            print(f"  verified {index:,}/{len(rows):,} files", flush=True)
    return {
        "verified": not missing and not mismatches,
        "missing": missing,
        "mismatches": mismatches,
    }


def verify_target(root: Path, baseline: Path, quick: bool) -> dict[str, Any]:
    manifest = read_json(baseline / "ISOLATED_TARGET_MANIFEST.json")
    target = root / Path(manifest["relative_path"])
    if quick:
        return {
            "verified": target.is_dir() and not target.is_symlink(),
            "quick": True,
            "target": str(target),
        }
    rows = manifest["files"]
    result = verify_rows(target, rows, "isolated target", progress=True)
    actual = {
        p.relative_to(target).as_posix().casefold()
        for p in target.rglob("*")
        if p.is_file() and not p.is_symlink()
    }
    expected = {str(row["path"]).casefold() for row in rows}
    result["unexpected"] = sorted(actual - expected)
    result["verified"] = bool(result["verified"] and not result["unexpected"])
    if result["verified"]:
        aggregate = hashlib.sha256()
        total = 0
        for row in rows:
            aggregate.update(str(row["path"]).casefold().encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(str(row["size_bytes"]).encode("ascii"))
            aggregate.update(b"\0")
            aggregate.update(str(row["sha256"]).encode("ascii"))
            aggregate.update(b"\n")
            total += int(row["size_bytes"])
        result.update(
            {
                "file_count": len(rows),
                "total_bytes": total,
                "tree_sha256": aggregate.hexdigest(),
            }
        )
        result["verified"] = (
            result["file_count"] == manifest["file_count"]
            and result["total_bytes"] == manifest["total_bytes"]
            and result["tree_sha256"] == manifest["tree_sha256"]
        )
    return result


def verify_historical(root: Path, pointer: dict[str, Any]) -> dict[str, Any]:
    results = []
    for row in pointer.get("historical_baselines", []):
        path = root / Path(row["baseline_relative_path"])
        tree = baseline_tree(path) if path.is_dir() else {
            "verified": False,
            "file_count": 0,
            "tree_sha256": "",
            "issues": ["missing"],
        }
        ok = (
            tree["verified"]
            and tree["file_count"] == row["baseline_file_count"]
            and tree["tree_sha256"] == row["baseline_tree_sha256"]
        )
        results.append(
            {
                "baseline_id": row["baseline_id"],
                "verified": ok,
                "actual": tree,
            }
        )
    return {
        "verified": all(row["verified"] for row in results),
        "baselines": results,
    }


def verify_known_good(root: Path, quick: bool = False) -> dict[str, Any]:
    pointer_path = root / POINTER
    if not pointer_path.is_file() or pointer_path.is_symlink():
        return {"verified": False, "error": "baseline pointer missing or unsafe"}
    pointer = read_json(pointer_path)
    baseline = root / Path(pointer["baseline_relative_path"])
    if not baseline.is_dir() or baseline.is_symlink():
        return {"verified": False, "error": "current baseline missing or unsafe"}
    tree = baseline_tree(baseline)
    if not (
        tree["verified"]
        and tree["file_count"] == pointer["baseline_file_count"]
        and tree["tree_sha256"] == pointer["baseline_tree_sha256"]
    ):
        return {"verified": False, "error": "baseline tree mismatch", "tree": tree}
    seal = read_json(baseline / "BASELINE_SEAL.json")
    if (
        seal.get("classification") != pointer.get("classification")
        or seal.get("classification") not in ALLOWED_CLASSIFICATIONS
    ):
        return {"verified": False, "error": "baseline classification mismatch"}
    integrated = verify_rows(
        root,
        read_json(baseline / "INTEGRATED_FILES_MANIFEST.json")["files"],
        "integrated",
    )
    protected = verify_rows(
        root,
        read_json(baseline / "PROTECTED_FILES_MANIFEST.json")["files"],
        "protected",
    )
    historical = verify_historical(root, pointer)
    profile_result: dict[str, Any] = {"verified": True, "present": False}
    profile_path = baseline / "DUAL_PROFILE_POLICY.json"
    if profile_path.is_file():
        policy = read_json(profile_path)
        node = policy["approved_node"]
        node_result = verify_rows(root, [node], "approved node")
        profile_result = {
            "verified": (
                policy.get("contract_id") == "FOXAI_COMFYUI_DUAL_CPU_PROFILE_V1"
                and policy.get("default_profile_id") == "safe-normal-cpu"
                and policy.get("approved_profile_id")
                == "approved-custom-nodes-cpu"
                and node_result["verified"]
            ),
            "present": True,
            "approved_node": node_result,
        }
    target = verify_target(root, baseline, quick)
    verified = all(
        [
            integrated["verified"],
            protected["verified"],
            historical["verified"],
            profile_result["verified"],
            target["verified"],
        ]
    )
    return {
        "verified": verified,
        "baseline_id": pointer["baseline_id"],
        "classification": pointer["classification"],
        "quick": quick,
        "baseline_tree": tree,
        "integrated": integrated,
        "protected": protected,
        "historical": historical,
        "profile": profile_result,
        "target": target,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the current sealed FOXAI ComfyUI baseline."
    )
    parser.add_argument("--root", type=Path)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Verify metadata and critical files without hashing all runtime files.",
    )
    args = parser.parse_args()
    script = Path(__file__).resolve()
    root = args.root.resolve() if args.root else script.parents[2]
    result = verify_known_good(root, quick=args.quick)
    if not result.get("verified"):
        print(f"[FAILED] {result.get('error', 'known-good verification failed')}")
        return 19
    print("[VERIFIED] FOXAI ComfyUI matches the current known-good baseline.")
    print(f"Baseline: {result['baseline_id']}")
    print(f"Classification: {result['classification']}")
    print(f"Mode: {'quick' if args.quick else 'full 39,046-file verification'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
