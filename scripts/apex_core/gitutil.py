"""Thin, read-only git helpers. All return None/[] when git is unavailable."""
from __future__ import annotations

import os
import subprocess


def _git(root: str, *args: str, timeout: int = 20) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", root, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def toplevel(root: str) -> str | None:
    out = _git(root, "rev-parse", "--show-toplevel")
    return os.path.realpath(out.strip()) if out else None


def head_sha(root: str, short: bool = False) -> str | None:
    args = ["rev-parse", "--short", "HEAD"] if short else ["rev-parse", "HEAD"]
    out = _git(root, *args)
    return out.strip() if out else None


def commit_exists(root: str, sha: str) -> bool:
    return bool(sha) and _git(root, "cat-file", "-e", f"{sha}^{{commit}}") is not None


def show_head(root: str, path: str) -> str | None:
    """Content of `path` (absolute) at HEAD, or None if untracked/no git."""
    top = toplevel(root)
    if not top:
        return None
    relpath = os.path.relpath(os.path.realpath(path), top).replace(os.sep, "/")
    if relpath.startswith(".."):
        return None
    return _git(root, "show", f"HEAD:{relpath}")


def changed_files(root: str, since: str) -> list[str]:
    out = _git(root, "diff", "--name-only", f"{since}..HEAD")
    return [l for l in (out or "").splitlines() if l.strip()]


def dirty_files(root: str) -> list[str]:
    """Modified, staged, and untracked files relative to the repo top."""
    out = _git(root, "status", "--porcelain", "--untracked-files=all")
    files = []
    for line in (out or "").splitlines():
        if len(line) > 3:
            name = line[3:]
            if " -> " in name:
                name = name.split(" -> ", 1)[1]
            files.append(name.strip().strip('"'))
    return files


def commits_since(root: str, since: str | None, limit: int = 200) -> list[str]:
    rng = f"{since}..HEAD" if since else "HEAD"
    out = _git(root, "log", "--oneline", f"-{limit}", rng)
    return [l for l in (out or "").splitlines() if l.strip()]


def current_branch(root: str) -> str | None:
    out = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip() if out else None
