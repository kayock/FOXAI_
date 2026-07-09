from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from datetime import datetime
import hashlib
import json
import shutil


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class UpdateCenter:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.outbox = self.foxai_root / "OpsBridge" / "outbox"
        self.outbox.mkdir(parents=True, exist_ok=True)

    def is_inside(self, child: Path, parent: Path) -> bool:
        try:
            child.resolve().relative_to(parent.resolve())
            return True
        except ValueError:
            return False

    def iter_files(self, package_root: Path) -> list[Path]:
        ignored = {"INSTALL_UPDATE.bat", "PREVIEW_UPDATE.bat", "APPLY_UPDATE.py", "README.txt"}
        files = []
        for p in package_root.rglob("*"):
            if not p.is_file():
                continue
            if p.name in ignored or "__pycache__" in p.parts:
                continue
            files.append(p)
        return files

    def preview(self, package_root: str | Path) -> dict[str, Any]:
        package_root = Path(package_root).resolve()
        report = {
            "ok": True,
            "mode": "preview",
            "package_root": str(package_root),
            "foxai_root": str(self.foxai_root),
            "cyclic_copy_risk": False,
            "warnings": [],
            "errors": [],
            "files": [],
        }

        if not package_root.exists():
            report["ok"] = False
            report["errors"].append(f"Package root not found: {package_root}")
            return report

        if package_root == self.foxai_root or self.is_inside(package_root, self.foxai_root):
            report["cyclic_copy_risk"] = True
            report["warnings"].append("Package is inside FOXAI root. Safe file-by-file update mode is active.")

        for src in self.iter_files(package_root):
            rel = src.relative_to(package_root)
            dest = self.foxai_root / rel
            action = "add"
            same = False
            if dest.exists():
                same = sha256(src) == sha256(dest)
                action = "skip_same" if same else "replace"
            report["files"].append({
                "relative_path": str(rel),
                "source": str(src),
                "destination": str(dest),
                "action": action,
                "same": same,
            })
        return report

    def apply(self, package_root: str | Path) -> dict[str, Any]:
        report = self.preview(package_root)
        report["mode"] = "apply"
        report["applied"] = []
        report["backups"] = []

        if not report.get("ok"):
            self.write_report(report)
            return report

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_root = self.foxai_root / "Backups" / f"update_center_{stamp}"
        backup_root.mkdir(parents=True, exist_ok=True)
        report["backup_root"] = str(backup_root)

        for item in report["files"]:
            if item["action"] == "skip_same":
                continue
            src = Path(item["source"])
            dest = Path(item["destination"])
            rel = Path(item["relative_path"])

            if dest.exists():
                backup_dest = backup_root / rel
                backup_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, backup_dest)
                report["backups"].append({"relative_path": str(rel), "backup": str(backup_dest)})

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            report["applied"].append({"relative_path": str(rel), "action": item["action"]})

        report["completed"] = datetime.now().isoformat(timespec="seconds")
        self.write_report(report)
        self.publish_event(report)
        return report

    def publish_event(self, report: dict[str, Any]) -> None:
        try:
            from .event_bus import EventBus
            from .captains_log import CaptainsLog
            bus = EventBus(self.foxai_root)
            bus.publish(
                event_type="update.applied",
                source="FOXAI Update Center",
                message=f"Update applied: {len(report.get('applied', []))} file(s), {len(report.get('backups', []))} backup(s).",
                payload={"applied": len(report.get("applied", [])), "backups": len(report.get("backups", []))},
                severity="success",
                channel="bridge",
            )
            CaptainsLog(self.foxai_root).build(limit=50)
        except Exception:
            pass

    def write_report(self, report: dict[str, Any]) -> None:
        (self.outbox / "update_center_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (self.outbox / "update_center_report.txt").write_text(self.render_text(report), encoding="utf-8")

    def render_text(self, report: dict[str, Any]) -> str:
        lines = [
            "FOXAI Update Center Report",
            "==========================",
            "",
            f"OK: {report.get('ok')}",
            f"Mode: {report.get('mode')}",
            f"Cyclic Copy Risk: {report.get('cyclic_copy_risk')}",
            f"Package: {report.get('package_root')}",
            f"FOXAI Root: {report.get('foxai_root')}",
            "",
        ]
        if report.get("warnings"):
            lines.append("Warnings:")
            for w in report["warnings"]:
                lines.append(f"- {w}")
            lines.append("")
        lines.append("Files:")
        for item in report.get("files", []):
            lines.append(f"- {item['relative_path']} [{item['action']}]")
        if "applied" in report:
            lines += ["", f"Applied: {len(report.get('applied', []))}", f"Backups: {len(report.get('backups', []))}"]
            if report.get("backup_root"):
                lines.append(f"Backup Root: {report['backup_root']}")
        return "\n".join(lines)
