from pathlib import Path
import zipfile
import datetime
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "Foundry" / "Releases"
REPORTS = ROOT / "Foundry" / "Reports"

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "out",
    "__pycache__",
    "Backups",
    "System/Temp",
}

EXCLUDE_SUFFIXES = {
    ".pyc",
    ".log",
}

LARGE_MODEL_SUFFIXES = {
    ".gguf",
    ".safetensors",
    ".ckpt",
    ".bin",
    ".onnx",
    ".pt",
    ".pth",
}

def read_manifest():
    text = (ROOT / "manifest.yaml").read_text(encoding="utf-8", errors="replace") if (ROOT / "manifest.yaml").exists() else ""
    version = "unknown"
    codename = "unknown"
    for line in text.splitlines():
        if line.strip().startswith("version:") and version == "unknown":
            version = line.split(":", 1)[1].strip()
        if line.strip().startswith("codename:") and codename == "unknown":
            codename = line.split(":", 1)[1].strip()
    return version, codename

def should_exclude(path):
    rel = path.relative_to(ROOT).as_posix()
    parts = rel.split("/")
    for i in range(1, len(parts) + 1):
        if "/".join(parts[:i]) in EXCLUDE_DIRS:
            return True
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    if path.suffix.lower() in LARGE_MODEL_SUFFIXES:
        return True
    return False

def create_release_zip():
    RELEASES.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    version, codename = read_manifest()
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_codename = "".join(c if c.isalnum() else "_" for c in codename).strip("_")
    zip_path = RELEASES / f"KayocktheOS_{version}_{safe_codename}_{stamp}.zip"

    included = []
    skipped = []

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in ROOT.rglob("*"):
            if path.is_dir():
                continue
            if should_exclude(path):
                skipped.append(path.relative_to(ROOT).as_posix())
                continue
            rel = path.relative_to(ROOT)
            z.write(path, rel)
            included.append(rel.as_posix())

    report = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "version": version,
        "codename": codename,
        "zip": str(zip_path),
        "included_files": len(included),
        "skipped_files": len(skipped),
        "skipped_examples": skipped[:50],
    }
    (REPORTS / "last_release_package.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return zip_path

if __name__ == "__main__":
    create_release_zip()
