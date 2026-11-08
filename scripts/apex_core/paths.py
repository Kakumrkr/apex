"""Filesystem layout of the `.apex/` state directory."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ApexPaths:
    root: str  # project root

    @property
    def apex(self) -> str:
        return os.path.join(self.root, ".apex")

    def p(self, *parts: str) -> str:
        return os.path.join(self.apex, *parts)

    @property
    def north_star(self) -> str:
        return self.p("north-star.md")

    @property
    def decisions(self) -> str:
        return self.p("decisions.md")

    @property
    def config(self) -> str:
        return self.p("config.json")

    @property
    def state(self) -> str:
        return self.p("state.json")

    @property
    def roadmap(self) -> str:
        return self.p("roadmap.md")

    @property
    def sessions_dir(self) -> str:
        return self.p("sessions")

    @property
    def research_dir(self) -> str:
        return self.p("research")

    @property
    def competitors(self) -> str:
        return self.p("research", "competitors.md")

    @property
    def history_dir(self) -> str:
        return self.p("history")

    @property
    def lock(self) -> str:
        return self.p(".lock")

    @property
    def search_log(self) -> str:
        return self.p(".search-log.json")

    @property
    def health(self) -> str:
        return self.p(".health.json")

    def exists(self) -> bool:
        return os.path.isdir(self.apex)


def resolve_root(project_dir: str | None = None) -> str:
    """Project root: explicit flag > $CLAUDE_PROJECT_DIR > cwd."""
    root = project_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.realpath(os.path.abspath(root))


def paths_for(project_dir: str | None = None) -> ApexPaths:
    return ApexPaths(resolve_root(project_dir))


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def read_text(path: str, default: str = "") -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (FileNotFoundError, IsADirectoryError):
        return default


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)
