"""Session Context Packets (`.apex/sessions/S-###-slug.md`)."""
from __future__ import annotations

import datetime as _dt
import glob
import os
import re

from . import fm, gitutil
from .paths import ApexPaths, read_text, write_text

STATUSES = ("todo", "in_progress", "done", "blocked", "dropped")
REQUIRED = ("id", "slug", "title", "status", "model", "parallel", "depends_on",
            "targets", "patterns", "do_not_touch", "estimate_hours", "dod",
            "planned_at_sha", "opportunity")
REQUIRED_SECTIONS = ("Goal", "Context", "Steps", "Definition of Done",
                     "Risk & Rollback", "Ready-to-run prompt")
MAX_TARGETS = 5
ID_RE = re.compile(r"^S-\d{3,}$")


def files(p: ApexPaths) -> list[str]:
    return sorted(glob.glob(os.path.join(p.sessions_dir, "S-*.md")))


def load_one(path: str) -> dict:
    data, body = fm.parse(read_text(path))
    data = dict(data)
    data["_keys"] = set(data)
    data["_path"] = path
    data["_body"] = body
    for key in ("depends_on", "targets", "patterns", "do_not_touch", "dod"):
        v = data.get(key)
        if v is None:
            data[key] = []
        elif not isinstance(v, list):
            data[key] = [v]
    return data


def load_all(p: ApexPaths) -> list[dict]:
    return [load_one(f) for f in files(p)]


def find(p: ApexPaths, sid: str) -> dict | None:
    sid = normalize_id(sid)
    for s in load_all(p):
        if s.get("id") == sid:
            return s
    return None


def normalize_id(sid: str) -> str:
    sid = str(sid).strip().upper()
    m = re.fullmatch(r"S?-?(\d+)", sid)
    return f"S-{int(m.group(1)):03d}" if m else sid


def by_id(sessions: list[dict]) -> dict:
    return {s.get("id"): s for s in sessions}


def ready(sessions: list[dict]) -> list[dict]:
    """`todo` sessions whose dependencies are all done."""
    idx = by_id(sessions)
    out = []
    for s in sessions:
        if s.get("status") != "todo":
            continue
        deps = s.get("depends_on") or []
        if all(idx.get(d, {}).get("status") == "done" for d in deps):
            out.append(s)
    return out


def parallel_batch(sessions: list[dict]) -> list[dict]:
    """Greedy set of ready, parallel-safe sessions with no target overlap."""
    batch, taken = [], set()
    for s in ready(sessions):
        if str(s.get("parallel")) != "safe":
            continue
        t = set(s.get("targets") or [])
        if t & taken:
            continue
        batch.append(s)
        taken |= t
    return batch


def set_status(p: ApexPaths, sid: str, status: str, notes: str | None = None,
               today: str | None = None) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    s = find(p, sid)
    if not s:
        raise ValueError(f"session {sid} not found in {p.sessions_dir}")
    cur = s.get("status")
    if cur == "done" and status != "done":
        raise ValueError(f"{s['id']} is already done; done packets are immutable")
    if status == "in_progress":
        idx = by_id(load_all(p))
        missing = [d for d in (s.get("depends_on") or []) if idx.get(d, {}).get("status") != "done"]
        if missing:
            raise ValueError(f"{s['id']} depends on unfinished sessions: {', '.join(missing)}")
    now = today or _dt.datetime.now().replace(microsecond=0).isoformat()
    updates = {"status": status}
    if status == "in_progress":
        updates["started_at"] = now
    if status == "done":
        updates["completed_at"] = now
    if notes:
        updates["notes"] = notes
    text = fm.set_fields(read_text(s["_path"]), updates)
    write_text(s["_path"], text)
    return find(p, s["id"])


def staleness(p: ApexPaths, s: dict) -> list[str]:
    """Target files changed since the packet was planned."""
    sha = s.get("planned_at_sha")
    if not sha or not gitutil.commit_exists(p.root, str(sha)):
        return []
    top = gitutil.toplevel(p.root) or p.root
    changed = set(gitutil.changed_files(p.root, str(sha)))
    prefix = os.path.relpath(p.root, top).replace(os.sep, "/")
    prefix = "" if prefix == "." else prefix + "/"
    return [t for t in (s.get("targets") or []) if prefix + t in changed]


def _match(path: str, pattern: str) -> bool:
    pattern = pattern.rstrip("/")
    if any(c in pattern for c in "*?["):
        import fnmatch
        return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, pattern + "/*")
    return path == pattern or path.startswith(pattern + "/")


def scope_report(p: ApexPaths, s: dict) -> dict:
    """Compare the working tree's changed files with the packet's scope."""
    top = gitutil.toplevel(p.root) or p.root
    prefix = os.path.relpath(p.root, top).replace(os.sep, "/")
    prefix = "" if prefix == "." else prefix + "/"
    changed = []
    for f in gitutil.dirty_files(p.root):
        if prefix and not f.startswith(prefix):
            continue
        changed.append(f[len(prefix):])
    targets = s.get("targets") or []
    dnt = s.get("do_not_touch") or []
    violations = [f for f in changed if any(_match(f, d) for d in dnt)]
    extra = [f for f in changed
             if not f.startswith(".apex/") and not any(_match(f, t) for t in targets)
             and f not in violations]
    return {"changed": changed, "do_not_touch_violations": violations, "out_of_scope": extra}
