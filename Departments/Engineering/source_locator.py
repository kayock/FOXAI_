from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .policy import DEFAULT_EXCLUDED_DIR_NAMES, ensure_project_root


@dataclass(slots=True)
class LocatedFile:
    path: Path
    relative_path: str
    score: int
    reason: str


class SourceLocator:
    def __init__(self, excluded_names: Iterable[str] | None = None):
        self.excluded_names = {
            name.lower() for name in (excluded_names or DEFAULT_EXCLUDED_DIR_NAMES)
        }

    def _excluded(self, relative: Path) -> bool:
        return any(part.lower() in self.excluded_names for part in relative.parts[:-1])

    def locate(
        self,
        project_root: str | Path,
        terms: Iterable[str],
        *,
        suffixes: tuple[str, ...] = (".py", ".js", ".ts", ".html", ".json", ".md", ".bat"),
        max_files: int = 5000,
        max_results: int = 100,
    ) -> list[LocatedFile]:
        root = ensure_project_root(Path(project_root))
        needles = [term.casefold() for term in terms if term.strip()]
        results: list[LocatedFile] = []
        seen = 0

        for path in root.rglob("*"):
            if seen >= max_files:
                break
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root)
            if self._excluded(relative):
                continue
            if suffixes and path.suffix.lower() not in suffixes:
                continue
            seen += 1
            name_text = str(relative).casefold()
            name_score = sum(20 for needle in needles if needle in name_text)
            content_score = 0
            reasons: list[str] = []
            if name_score:
                reasons.append("path matched")
            try:
                if path.stat().st_size <= 2 * 1024 * 1024:
                    content = path.read_text(encoding="utf-8", errors="ignore").casefold()
                    content_score = sum(min(10, content.count(needle)) * 2 for needle in needles)
                    if content_score:
                        reasons.append("content matched")
            except OSError:
                continue
            score = name_score + content_score
            if score:
                results.append(
                    LocatedFile(path, relative.as_posix(), score, ", ".join(reasons))
                )

        return sorted(results, key=lambda item: (-item.score, item.relative_path))[:max_results]
