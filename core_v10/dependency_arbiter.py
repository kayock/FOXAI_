from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import ast, json, re

@dataclass
class DependencyArbiter:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.core = self.foxai_root / "core_v10"

    @property
    def outbox(self) -> Path:
        p = self.foxai_root / "OpsBridge" / "outbox"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def module_name(self, path: Path) -> str:
        return ".".join(path.relative_to(self.foxai_root).with_suffix("").parts)

    def file_for_module(self, module: str) -> Path | None:
        parts = module.split(".")
        py = self.foxai_root / Path(*parts).with_suffix(".py")
        init = self.foxai_root / Path(*parts) / "__init__.py"
        if py.exists(): return py
        if init.exists(): return init
        return None

    def exports_for_file(self, path: Path) -> set[str]:
        exports = set()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return exports
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                exports.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name): exports.add(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                exports.add(node.target.id)
        return exports

    def resolve_relative(self, current_module: str, module: str | None, level: int) -> str:
        if level <= 0:
            return module or ""
        base = current_module.split(".")[:-1]
        if level > 1:
            base = base[:-(level - 1)] if (level - 1) <= len(base) else []
        if module:
            base += module.split(".")
        return ".".join(base)

    def scan_file(self, path: Path) -> dict[str, Any]:
        module_name = self.module_name(path)
        imports, problems = [], []
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        except Exception as e:
            return {"ok": False, "file": str(path), "module": module_name, "imports": [], "problems": [{"type": "parse_error", "message": str(e)}]}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.append({"kind": "import", "module": a.name, "name": None, "lineno": getattr(node, "lineno", None)})
            elif isinstance(node, ast.ImportFrom):
                mod = self.resolve_relative(module_name, node.module, node.level)
                for a in node.names:
                    imports.append({"kind": "from", "module": mod, "name": a.name, "lineno": getattr(node, "lineno", None)})

        for imp in imports:
            mod, name = imp["module"], imp.get("name")
            if not mod.startswith("core_v10"):
                continue
            target = self.file_for_module(mod)
            if target is None:
                problems.append({"type": "missing_module", "lineno": imp.get("lineno"), "module": mod, "name": name, "message": f"Missing project module: {mod}"})
                continue
            if imp["kind"] == "from" and name and name != "*":
                if name not in self.exports_for_file(target):
                    problems.append({"type": "missing_export", "lineno": imp.get("lineno"), "module": mod, "name": name, "module_file": str(target), "message": f"{mod} does not export {name}"})
        return {"ok": not problems, "file": str(path), "module": module_name, "imports": imports, "problems": problems}

    def recommendations(self, problems: list[dict[str, Any]]) -> list[dict[str, str]]:
        recs = []
        for p in problems:
            if p.get("type") == "missing_export" and p.get("name") == "list_professors":
                recs.append({
                    "priority": "high",
                    "title": "Restore Academy compatibility export",
                    "reason": "foxai_core imports list_professors, but core_v10.academy does not export it.",
                    "suggestion": "Add a compatibility function list_professors() to core_v10/academy/__init__.py or update foxai_core.py to use the new professor registry."
                })
        return recs or [{"priority": "info", "title": "Review dependency report", "reason": "No targeted repair suggestion matched.", "suggestion": "Review missing_module and missing_export items manually."}]

    def scan(self) -> dict[str, Any]:
        files = sorted(self.core.rglob("*.py"))
        reports = [self.scan_file(p) for p in files]
        problems = []
        edges = []
        for r in reports:
            for p in r["problems"]:
                item = dict(p); item["file"] = r["file"]; item["source_module"] = r["module"]; problems.append(item)
            for i in r["imports"]:
                if i.get("module", "").startswith("core_v10"):
                    edges.append({"from": r["module"], "to": i["module"], "name": i.get("name"), "lineno": i.get("lineno")})
        return {"ok": not problems, "scanner": "USS Dependency Arbiter", "version": "CM v6.1", "root": str(self.foxai_root), "files_scanned": len(files), "project_import_edges": len(edges), "problem_count": len(problems), "problems": problems, "edges": edges, "files": reports, "recommendations": self.recommendations(problems)}

    def write_reports(self, report: dict[str, Any]) -> dict[str, str]:
        jp = self.outbox / "dependency_report.json"
        tp = self.outbox / "dependency_report.txt"
        jp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        tp.write_text(self.render_text(report), encoding="utf-8")
        return {"json": str(jp), "txt": str(tp)}

    def render_text(self, report: dict[str, Any]) -> str:
        lines = ["FOXAI CM v6.1 - USS Dependency Arbiter", "======================================", "", f"OK: {report.get('ok')}", f"Files Scanned: {report.get('files_scanned')}", f"Project Import Edges: {report.get('project_import_edges')}", f"Problems: {report.get('problem_count')}", ""]
        lines.append("Problems:")
        if report.get("problems"):
            for p in report["problems"]:
                lines += [f"- {p.get('type')} in {p.get('source_module')} line {p.get('lineno')}", f"  {p.get('message')}", f"  File: {p.get('file')}"]
                if p.get("module_file"): lines.append(f"  Target: {p.get('module_file')}")
        else:
            lines.append("- None detected.")
        lines += ["", "Recommendations:"]
        for r in report.get("recommendations", []):
            lines += [f"- [{r.get('priority')}] {r.get('title')}", f"  Reason: {r.get('reason')}", f"  Suggestion: {r.get('suggestion')}"]
        return "\n".join(lines)
