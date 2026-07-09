from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import importlib.util
import sys

from .service_container import ServiceContainer


CORE_PACKAGES = [
    "pluggy",
    "watchdog",
    "psutil",
    "requests",
    "rich",
    "textual",
    "rapidfuzz",
    "pydantic",
    "networkx",
    "plotly",
    "jsonschema",
    "dependency_injector",
    "stevedore",
    "blinker",
    "git",
    "orjson",
]


PACKAGE_IMPORT_ALIASES = {
    "GitPython": "git",
    "gitpython": "git",
    "dependency-injector": "dependency_injector",
}


@dataclass
class TechnologyOfficer:
    foxai_root: Path

    def __post_init__(self) -> None:
        self.foxai_root = Path(self.foxai_root).resolve()
        self.container = ServiceContainer(self.foxai_root)

    @property
    def hanger_bay(self) -> Path:
        # FOXAI root is usually Z:\FOXAI, Hangar/Hanger Bay is sibling on the same drive.
        candidates = [
            self.foxai_root.parent / "Hanger Bay",
            self.foxai_root.parent / "Hangar Bay",
            Path("Z:/Hanger Bay"),
            Path("Z:/Hangar Bay"),
        ]
        for c in candidates:
            if c.exists():
                return c
        return self.foxai_root.parent / "Hanger Bay"

    def _find_package(self, package: str) -> dict[str, Any]:
        import_name = PACKAGE_IMPORT_ALIASES.get(package, package)

        # 1. Active Python environment
        if importlib.util.find_spec(import_name) is not None:
            return {
                "package": package,
                "import_name": import_name,
                "installed": True,
                "status": "ready",
                "source": "active_python",
                "path": "",
            }

        # 2. Portable Hanger Bay package target
        hb = self.hanger_bay
        if hb.exists():
            package_dir_names = [
                import_name,
                package,
                package.replace("-", "_"),
                package.replace("_", "-"),
            ]

            for name in package_dir_names:
                p = hb / name
                if p.exists():
                    return {
                        "package": package,
                        "import_name": import_name,
                        "installed": True,
                        "status": "ready",
                        "source": "hanger_bay",
                        "path": str(p),
                    }

            # Dist-info fallback, useful for packages where import name differs.
            patterns = [
                f"{package.replace('_', '-')}*.dist-info",
                f"{package.replace('-', '_')}*.dist-info",
                f"{import_name.replace('_', '-')}*.dist-info",
                f"{import_name.replace('-', '_')}*.dist-info",
            ]
            for pattern in patterns:
                matches = list(hb.glob(pattern))
                if matches:
                    return {
                        "package": package,
                        "import_name": import_name,
                        "installed": True,
                        "status": "ready",
                        "source": "hanger_bay_dist_info",
                        "path": str(matches[0]),
                    }

        return {
            "package": package,
            "import_name": import_name,
            "installed": False,
            "status": "missing",
            "source": "not_found",
            "path": "",
        }

    def inspect_environment(self) -> dict[str, Any]:
        packages = [self._find_package(pkg) for pkg in CORE_PACKAGES]
        by_source: dict[str, int] = {}
        for p in packages:
            by_source[p["source"]] = by_source.get(p["source"], 0) + 1

        return {
            "ok": True,
            "hanger_bay": str(self.hanger_bay),
            "packages": packages,
            "installed_count": sum(1 for p in packages if p["installed"]),
            "missing_count": sum(1 for p in packages if not p["installed"]),
            "by_source": by_source,
            "sys_path_hint": "Portable packages can be detected in Hanger Bay even if not importable by active Python.",
        }

    def readiness_score(self, service_health: dict[str, Any], env: dict[str, Any]) -> dict[str, Any]:
        service_total = max(1, service_health.get("total", 1))
        service_ok = sum(1 for x in service_health.get("items", []) if x.get("ok"))
        service_score = service_ok / service_total

        pkg_total = max(1, len(env.get("packages", [])))
        pkg_ok = env.get("installed_count", 0)
        package_score = pkg_ok / pkg_total

        overall = round(((service_score * 0.65) + (package_score * 0.35)) * 100)

        return {
            "overall": overall,
            "services": round(service_score * 100),
            "packages": round(package_score * 100),
        }

    def recommendations(self, env: dict[str, Any], service_health: dict[str, Any]) -> list[dict[str, Any]]:
        recs = []

        missing = [p["package"] for p in env.get("packages", []) if not p["installed"]]
        for pkg in missing:
            if pkg == "git":
                recs.append({
                    "priority": 4,
                    "title": "Install GitPython",
                    "reason": "Enables repository intelligence for Technology Officer.",
                    "command": "pip install GitPython",
                })
            elif pkg == "orjson":
                recs.append({
                    "priority": 3,
                    "title": "Install orjson",
                    "reason": "Faster JSON handling for manifests, reports, and registries.",
                    "command": "pip install orjson",
                })
            else:
                recs.append({
                    "priority": 2,
                    "title": f"Install {pkg}",
                    "reason": f"{pkg} is part of the planned FOXAI service stack.",
                    "command": f"pip install {pkg}",
                })

        if not service_health.get("ok"):
            recs.append({
                "priority": 5,
                "title": "Repair service container",
                "reason": "At least one core service failed health inspection.",
                "command": "Run ENGINEERING_REPORT.bat and inspect service errors.",
            })

        return sorted(recs, key=lambda x: x["priority"], reverse=True)

    def engineering_report(self) -> dict[str, Any]:
        services = self.container.health()
        env = self.inspect_environment()
        readiness = self.readiness_score(services, env)

        return {
            "ok": services.get("ok", False),
            "system": "FOXAI Technology Officer",
            "mission": "CM v3.3b Portable Package Detection",
            "readiness": readiness,
            "services": services,
            "environment": env,
            "contracts": self.container.contract_dicts(),
            "recommendations": self.recommendations(env, services),
        }
