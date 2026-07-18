#!/usr/bin/env python3
"""Portable-runtime verifier for FOXAI USB C3E.

This script is launched by the protected portable CPython with -I -B -S. It
adds only the candidate isolated target with site.addsitedir(), deliberately
executes the reviewed .pth behavior, and verifies that the exact locked package
set is internally complete and imports without host paths.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib
import importlib.metadata as metadata
import io
import json
import os
import re
import site
import sys
import traceback
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_PTH_TEXT = "import os; var = 'SETUPTOOLS_USE_DISTUTILS'; enabled = os.environ.get(var, 'local') == 'local'; enabled and __import__('_distutils_hack').add_shim(); "
EXPECTED_VERSIONS = {
    "torch": "2.12.1",
    "torchvision": "0.27.1",
    "torchaudio": "2.11.0",
}
CRITICAL_DISTRIBUTIONS = {
    "aiohttp", "av", "blake3", "charset-normalizer", "comfy-aimdo",
    "comfy-angle", "comfy-kitchen", "cryptography", "frozenlist",
    "greenlet", "hf-xet", "huggingface-hub", "kornia", "kornia-rs",
    "markupsafe", "multidict", "numpy", "packaging", "pillow",
    "propcache", "psutil", "pydantic", "pydantic-core", "pynacl",
    "pyyaml", "regex", "safetensors", "scipy", "sentencepiece",
    "setuptools", "sqlalchemy", "tokenizers", "torch", "torchaudio",
    "pyopengl",
    "torchvision", "transformers", "yarl",
}
PREFERRED_IMPORTS = {
    "aiohttp": ["aiohttp"],
    "av": ["av"],
    "blake3": ["blake3"],
    "charset-normalizer": ["charset_normalizer"],
    "cryptography": ["cryptography"],
    "frozenlist": ["frozenlist"],
    "greenlet": ["greenlet"],
    "hf-xet": ["hf_xet"],
    "huggingface-hub": ["huggingface_hub"],
    "kornia": ["kornia"],
    "kornia-rs": ["kornia_rs"],
    "markupsafe": ["markupsafe"],
    "multidict": ["multidict"],
    "numpy": ["numpy"],
    "packaging": ["packaging"],
    "pillow": ["PIL"],
    "propcache": ["propcache"],
    "psutil": ["psutil"],
    "pydantic": ["pydantic"],
    "pydantic-core": ["pydantic_core"],
    "pynacl": ["nacl"],
    "pyopengl": ["OpenGL", "OpenGL.GL"],
    "pyyaml": ["yaml"],
    "regex": ["regex"],
    "safetensors": ["safetensors"],
    "scipy": ["scipy"],
    "sentencepiece": ["sentencepiece"],
    "setuptools": ["setuptools"],
    "sqlalchemy": ["sqlalchemy"],
    "tokenizers": ["tokenizers"],
    "torch": ["torch"],
    "torchaudio": ["torchaudio"],
    "torchvision": ["torchvision"],
    "transformers": ["transformers"],
    "yarl": ["yarl"],
}


def canonicalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", str(name)).lower()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except Exception:
        return False


def decode_record_hash(value: str) -> tuple[str, bytes] | None:
    if not value or "=" not in value:
        return None
    algorithm, encoded = value.split("=", 1)
    padding = "=" * (-len(encoded) % 4)
    return algorithm.lower(), base64.urlsafe_b64decode(encoded + padding)


def hash_file(path: Path, algorithm: str) -> bytes:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.digest()


def module_locations(module: Any) -> list[str]:
    locations: list[str] = []
    file_value = getattr(module, "__file__", None)
    if file_value:
        locations.append(str(Path(file_value).resolve(strict=False)))
    path_value = getattr(module, "__path__", None)
    if path_value:
        for item in path_value:
            locations.append(str(Path(item).resolve(strict=False)))
    return sorted(set(locations))


def infer_imports(dist: metadata.Distribution) -> list[str]:
    candidates: list[str] = []
    top_level = dist.read_text("top_level.txt")
    if top_level:
        for raw in top_level.splitlines():
            name = raw.strip()
            if name and name.isidentifier():
                candidates.append(name)
    files = dist.files or []
    if not candidates:
        for item in files:
            parts = PurePosixPath(str(item)).parts
            if not parts:
                continue
            first = parts[0]
            if first.endswith((".dist-info", ".data", ".libs")):
                continue
            if len(parts) == 1 and first.endswith(".py"):
                stem = first[:-3]
                if stem.isidentifier():
                    candidates.append(stem)
            elif first.isidentifier() and any(str(item).lower().endswith(ext) for ext in (".py", ".pyd")):
                candidates.append(first)
    return sorted(set(candidates))




def resolve_target_record_path(target: Path, record_path: str) -> Path:
    normalized = record_path.replace("\\", "/")
    logical = PurePosixPath(normalized)
    if logical.is_absolute():
        raise ValueError(f"absolute RECORD path is forbidden: {record_path}")
    parts = list(logical.parts)
    while parts and parts[0] in {".", ".."}:
        parts.pop(0)
    if not parts or any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise ValueError(f"unsafe RECORD path is forbidden: {record_path}")
    return target.joinpath(*parts).resolve(strict=False)

def verify_record(dist: metadata.Distribution, target: Path) -> dict[str, Any]:
    name = canonicalize_name(dist.metadata.get("Name", ""))
    version = str(dist.version)
    issues: list[str] = []
    rows: list[dict[str, Any]] = []
    blank_hashes: list[str] = []
    record_text = dist.read_text("RECORD")
    if record_text is None:
        return {"name": name, "version": version, "verified": False, "issues": ["distribution has no RECORD"], "files": []}
    try:
        parsed_rows = list(csv.reader(io.StringIO(record_text)))
    except Exception as exc:
        return {"name": name, "version": version, "verified": False, "issues": [f"RECORD parse failed: {type(exc).__name__}: {exc}"], "files": []}
    for row_number, fields in enumerate(parsed_rows, 1):
        if len(fields) != 3:
            issues.append(f"RECORD row {row_number} does not have exactly 3 columns")
            rows.append({"row_number": row_number, "fields": fields, "verified": False})
            continue
        relative, hash_text, size_text = fields
        relative = relative.replace("\\", "/")
        try:
            located = resolve_target_record_path(target, relative)
        except Exception as exc:
            issues.append(f"Unsafe RECORD path: {relative}: {type(exc).__name__}: {exc}")
            rows.append({"row_number": row_number, "record_path": relative, "verified": False, "issue": str(exc)})
            continue
        record: dict[str, Any] = {"row_number": row_number, "record_path": relative, "located": str(located)}
        if not is_within(located, target):
            issues.append(f"RECORD path escapes isolated target after target-relocation mapping: {relative} -> {located}")
            record["verified"] = False
            rows.append(record)
            continue
        if not located.is_file():
            issues.append(f"RECORD file is missing: {relative} -> {located}")
            record["verified"] = False
            rows.append(record)
            continue
        actual_size = located.stat().st_size
        record["actual_size"] = actual_size
        if size_text:
            try:
                expected_size = int(size_text)
                record["expected_size"] = expected_size
                if actual_size != expected_size:
                    issues.append(f"RECORD size mismatch: {relative}")
            except ValueError:
                issues.append(f"Malformed RECORD size: {relative} -> {size_text!r}")
        if hash_text:
            decoded = decode_record_hash(hash_text)
            if decoded is None:
                issues.append(f"Malformed RECORD hash: {relative}")
            else:
                algorithm, expected = decoded
                try:
                    actual = hash_file(located, algorithm)
                    if actual != expected:
                        issues.append(f"RECORD digest mismatch: {relative}")
                    record["hash_algorithm"] = algorithm
                    record["digest_verified"] = actual == expected
                except Exception as exc:
                    issues.append(f"Could not verify RECORD digest for {relative}: {type(exc).__name__}: {exc}")
        else:
            blank_hashes.append(relative)
            if not relative.endswith(".dist-info/RECORD"):
                issues.append(f"Unexpected blank RECORD hash: {relative}")
        record["verified"] = not any(relative in issue for issue in issues)
        rows.append(record)
    return {
        "name": name,
        "version": version,
        "verified": not issues,
        "issues": issues,
        "record_file_count": len(rows),
        "blank_hash_paths": blank_hashes,
        "files": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    target = Path(args.target).resolve(strict=True)
    lock_path = Path(args.lock).resolve(strict=True)
    output_path = Path(args.output)
    issues: list[str] = []
    result: dict[str, Any] = {
        "verified": False,
        "target": str(target),
        "python": sys.executable,
        "version": list(sys.version_info[:3]),
        "isolated_flag": sys.flags.isolated,
        "no_site_flag": sys.flags.no_site,
        "sys_path_before_activation": list(sys.path),
    }

    try:
        if tuple(sys.version_info[:3]) != (3, 14, 6):
            issues.append(f"portable Python version changed: {sys.version_info[:3]}")
        if not sys.flags.isolated:
            issues.append("verification interpreter is not running in isolated mode")
        if not sys.flags.no_site:
            issues.append("verification interpreter did not start with -S")
        if not target.is_dir():
            issues.append("candidate target is missing")

        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        entries = lock.get("entries") or []
        expected = {canonicalize_name(item["name"]): str(item["version"]) for item in entries}
        if len(expected) != 96:
            issues.append(f"lock does not contain 96 unique packages: {len(expected)}")

        os.environ.setdefault("SETUPTOOLS_USE_DISTUTILS", "local")
        site.addsitedir(str(target))
        result["sys_path_after_activation"] = list(sys.path)

        target_occurrences = [p for p in sys.path if Path(p).resolve(strict=False) == target]
        if len(target_occurrences) != 1:
            issues.append(f"isolated target appears {len(target_occurrences)} times in sys.path")
        forbidden_path_fragments = [
            r"c:\python314",
            r"\appdata\roaming\python",
            r"runtime\core",
        ]
        path_findings = []
        for item in sys.path:
            lowered = str(Path(item).resolve(strict=False)).lower()
            if any(fragment in lowered for fragment in forbidden_path_fragments):
                path_findings.append(str(item))
            if "site-packages" in lowered and not is_within(Path(item), target):
                path_findings.append(str(item))
        if path_findings:
            issues.append(f"forbidden host/core site paths are active: {sorted(set(path_findings))}")
        result["forbidden_sys_path_findings"] = sorted(set(path_findings))

        # The reviewed setuptools .pth line must have executed from the target.
        pth = target / "distutils-precedence.pth"
        pth_result = {"path": str(pth), "exists": pth.is_file(), "verified": False}
        if not pth.is_file():
            issues.append("reviewed distutils-precedence.pth is missing")
        else:
            pth_text = pth.read_text(encoding="utf-8")
            pth_result["text"] = pth_text
            pth_result["sha256"] = hashlib.sha256(pth.read_bytes()).hexdigest()
            if pth_text.strip() != EXPECTED_PTH_TEXT.strip():
                issues.append("distutils-precedence.pth content changed")
            hack = sys.modules.get("_distutils_hack")
            pth_result["distutils_hack_loaded"] = hack is not None
            pth_result["distutils_hack_locations"] = module_locations(hack) if hack else []
            pth_result["shim_finder_present"] = any(type(finder).__module__ == "_distutils_hack" for finder in sys.meta_path)
            if hack is None or not pth_result["shim_finder_present"]:
                issues.append("reviewed setuptools .pth activation did not install the distutils shim")
            for location in pth_result["distutils_hack_locations"]:
                if not is_within(Path(location), target):
                    issues.append(f"_distutils_hack loaded outside target: {location}")
            pth_result["verified"] = not any("distutils" in item.lower() or ".pth" in item.lower() for item in issues)
        result["pth_activation"] = pth_result

        # packaging must now come from the isolated target.
        from packaging.markers import default_environment
        from packaging.requirements import Requirement
        from packaging.version import Version

        distributions = list(metadata.distributions(path=[str(target)]))
        observed: dict[str, metadata.Distribution] = {}
        duplicates: list[str] = []
        inventory_rows = []
        for dist in distributions:
            name = canonicalize_name(dist.metadata.get("Name", ""))
            version = str(dist.version)
            dist_path = Path(getattr(dist, "_path", target)).resolve(strict=False)
            inventory_rows.append({"name": name, "version": version, "dist_info": str(dist_path)})
            if name in observed:
                duplicates.append(name)
            observed[name] = dist
            if not is_within(dist_path, target):
                issues.append(f"distribution metadata outside isolated target: {name} -> {dist_path}")
        result["distribution_inventory"] = {
            "count": len(distributions),
            "unique_count": len(observed),
            "duplicates": sorted(set(duplicates)),
            "rows": sorted(inventory_rows, key=lambda row: row["name"]),
        }
        if len(distributions) != 96 or len(observed) != 96 or duplicates:
            issues.append(f"installed distribution count mismatch: total={len(distributions)}, unique={len(observed)}, duplicates={duplicates}")
        missing = sorted(set(expected) - set(observed))
        unexpected = sorted(set(observed) - set(expected))
        version_mismatches = []
        for name, expected_version in expected.items():
            if name in observed and str(observed[name].version) != expected_version:
                version_mismatches.append({"name": name, "expected": expected_version, "actual": str(observed[name].version)})
        if missing:
            issues.append(f"missing locked distributions: {missing}")
        if unexpected:
            issues.append(f"unexpected distributions: {unexpected}")
        if version_mismatches:
            issues.append(f"locked version mismatches: {version_mismatches}")
        result["lock_comparison"] = {"missing": missing, "unexpected": unexpected, "version_mismatches": version_mismatches}

        record_results = []
        for name in sorted(observed):
            record_result = verify_record(observed[name], target)
            record_results.append(record_result)
            issues.extend(record_result["issues"])
        covered_paths = set()
        for record_result in record_results:
            for file_row in record_result.get("files", []):
                located = file_row.get("located")
                if located:
                    covered_paths.add(str(Path(located).resolve(strict=False)).casefold())
        actual_paths = {str(path.resolve(strict=False)).casefold() for path in target.rglob("*") if path.is_file()}
        uncovered_paths = sorted(actual_paths - covered_paths)
        referenced_missing = sorted(covered_paths - actual_paths)
        if uncovered_paths:
            issues.append(f"installed files not covered by any distribution RECORD: {uncovered_paths[:50]}")
        if referenced_missing:
            issues.append(f"distribution RECORD paths missing from target: {referenced_missing[:50]}")
        record_verified = all(item["verified"] for item in record_results) and not uncovered_paths and not referenced_missing
        result["installed_record_verification"] = {
            "verified": record_verified,
            "distribution_count": len(record_results),
            "covered_file_count": len(covered_paths),
            "actual_file_count": len(actual_paths),
            "uncovered_paths": uncovered_paths,
            "referenced_missing_paths": referenced_missing,
            "results": record_results,
        }

        environment = default_environment()
        environment["extra"] = ""
        dependency_results = []
        dependency_issues = []
        for name, dist in sorted(observed.items()):
            for raw_requirement in dist.requires or []:
                try:
                    req = Requirement(raw_requirement)
                    active = req.marker is None or req.marker.evaluate(environment)
                    row = {"owner": name, "raw": raw_requirement, "name": canonicalize_name(req.name), "active": active, "specifier": str(req.specifier), "verified": True}
                    if active:
                        dependency_name = canonicalize_name(req.name)
                        dependency = observed.get(dependency_name)
                        if dependency is None:
                            row["verified"] = False
                            row["issue"] = "active dependency missing"
                        elif req.specifier and Version(str(dependency.version)) not in req.specifier:
                            row["verified"] = False
                            row["issue"] = f"installed version {dependency.version} does not satisfy {req.specifier}"
                    if not row["verified"]:
                        dependency_issues.append(row)
                    dependency_results.append(row)
                except Exception as exc:
                    dependency_issues.append({"owner": name, "raw": raw_requirement, "issue": f"parse/evaluation failure: {type(exc).__name__}: {exc}"})
        if dependency_issues:
            issues.append(f"active dependency verification failed for {len(dependency_issues)} edge(s)")
        result["dependency_edges"] = {
            "verified": not dependency_issues,
            "edge_count": len(dependency_results),
            "issues": dependency_issues,
            "edges": dependency_results,
        }

        imports = []
        import_issues = []
        for dist_name in sorted(CRITICAL_DISTRIBUTIONS):
            dist = observed.get(dist_name)
            if dist is None:
                import_issues.append({"distribution": dist_name, "issue": "distribution missing"})
                continue
            candidates = PREFERRED_IMPORTS.get(dist_name) or infer_imports(dist)
            if not candidates:
                imports.append({"distribution": dist_name, "status": "data_only_or_no_import_candidate", "verified": True})
                continue
            imported_any = False
            candidate_errors = []
            for module_name in candidates:
                try:
                    module = importlib.import_module(module_name)
                    locations = module_locations(module)
                    outside = [location for location in locations if not is_within(Path(location), target)]
                    row = {"distribution": dist_name, "module": module_name, "locations": locations, "verified": bool(locations) and not outside, "outside_locations": outside}
                    imports.append(row)
                    imported_any = imported_any or row["verified"]
                    if outside or not locations:
                        candidate_errors.append(row)
                except Exception as exc:
                    candidate_errors.append({"distribution": dist_name, "module": module_name, "issue": f"{type(exc).__name__}: {exc}"})
            if not imported_any:
                import_issues.extend(candidate_errors or [{"distribution": dist_name, "issue": "no import candidate succeeded"}])
        if import_issues:
            issues.append(f"critical isolated imports failed for {len(import_issues)} candidate(s)")
        result["critical_imports"] = {"verified": not import_issues, "imports": imports, "issues": import_issues}

        torch_result: dict[str, Any] = {"verified": False}
        try:
            import torch
            import torchvision
            import torchvision.extension
            import torchaudio
            tensor = torch.tensor([[1.0, 2.0], [3.0, 4.0]], device="cpu")
            product = tensor @ tensor
            expected_product = [[7.0, 10.0], [15.0, 22.0]]
            torch_result = {
                "torch_version": str(torch.__version__),
                "torchvision_version": str(torchvision.__version__),
                "torchaudio_version": str(torchaudio.__version__),
                "torch_file": str(Path(torch.__file__).resolve()),
                "torchvision_file": str(Path(torchvision.__file__).resolve()),
                "torchaudio_file": str(Path(torchaudio.__file__).resolve()),
                "cpu_tensor_product": product.tolist(),
                "torchvision_compiled_ops": bool(torchvision.extension._has_ops()),
                "cuda_available": bool(torch.cuda.is_available()),
            }
            version_checks = {
                "torch": str(torch.__version__).split("+")[0] == EXPECTED_VERSIONS["torch"],
                "torchvision": str(torchvision.__version__).split("+")[0] == EXPECTED_VERSIONS["torchvision"],
                "torchaudio": str(torchaudio.__version__).split("+")[0] == EXPECTED_VERSIONS["torchaudio"],
            }
            location_checks = all(is_within(Path(path), target) for path in [torch_result["torch_file"], torch_result["torchvision_file"], torch_result["torchaudio_file"]])
            torch_result["version_checks"] = version_checks
            torch_result["location_checks"] = location_checks
            torch_result["verified"] = all(version_checks.values()) and location_checks and product.tolist() == expected_product and torch_result["torchvision_compiled_ops"]
            if not torch_result["verified"]:
                issues.append(f"torch-family verification failed: {torch_result}")
        except Exception as exc:
            torch_result["issue"] = f"{type(exc).__name__}: {exc}"
            issues.append(f"torch-family import or CPU smoke test failed: {type(exc).__name__}: {exc}")
        result["torch_family"] = torch_result

    except Exception as exc:
        issues.append(f"Verifier exception: {type(exc).__name__}: {exc}")
        result["exception"] = traceback.format_exc()

    result["issues"] = issues
    result["verified"] = not issues
    write_json(output_path, result)
    return 0 if result["verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
