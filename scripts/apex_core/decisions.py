"""The append-only Won't Fix / Deferred log (`.apex/decisions.md`)."""
from __future__ import annotations

import datetime as _dt
import re

from . import md
from .paths import ApexPaths, read_text, write_text

HEADER = """# Apex Decisions Log — Won't Fix & Deferred

> Managed by `apex.py decision add` (or `/apex:defer`). Append-only: Claude's
> Write/Edit tools are blocked on this file by the Apex hooks.
>
> - **WF** (won't fix): never suggest this again and never dock the score for it.
> - **DF** (deferred): may be re-proposed only after `revisit`, and the new
>   opportunity must list this ID in its `checked` column.

| ID | Type | Slug | Title | Reason | Date | Revisit |
|----|------|------|-------|--------|------|---------|
"""

TYPES = {"wont-fix": "WF", "deferred": "DF"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)[:60].strip("-") or "item"


def load(p: ApexPaths) -> list[dict]:
    text = read_text(p.decisions)
    rows = []
    for table in md.tables(text):
        for r in table:
            did = md.col(r, "id").strip()
            if not re.fullmatch(r"(WF|DF)-\d{3,}", did):
                continue
            rows.append({
                "id": did,
                "type": md.col(r, "type").strip(),
                "slug": md.col(r, "slug").strip().strip("`"),
                "title": md.col(r, "title").strip(),
                "reason": md.col(r, "reason").strip(),
                "date": md.col(r, "date").strip(),
                "revisit": md.col(r, "revisit").strip().strip("—-").strip() or None,
            })
    return rows


def ensure_file(p: ApexPaths) -> None:
    if not read_text(p.decisions).strip():
        write_text(p.decisions, HEADER)


def _cell(s: str) -> str:
    return (s or "").replace("\n", " ").replace("|", "\\|").strip()


def add(p: ApexPaths, kind: str, title: str, reason: str, slug: str | None = None,
        revisit: str | None = None, today: str | None = None) -> dict:
    if kind not in TYPES:
        raise ValueError(f"type must be one of {sorted(TYPES)}")
    if not title.strip():
        raise ValueError("title is required")
    if not reason.strip():
        raise ValueError("reason is required (future audits rely on it)")
    slug = slug or slugify(title)
    if not SLUG_RE.match(slug):
        raise ValueError(f"slug must be kebab-case: {slug!r}")
    if revisit and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", revisit):
        raise ValueError("revisit must be YYYY-MM-DD")
    ensure_file(p)
    existing = load(p)
    for e in existing:
        if e["slug"] == slug:
            raise ValueError(f"slug {slug!r} already recorded as {e['id']}")
    prefix = TYPES[kind]
    nums = [int(e["id"].split("-")[1]) for e in existing if e["id"].startswith(prefix)]
    did = f"{prefix}-{(max(nums) + 1) if nums else 1:03d}"
    today = today or _dt.date.today().isoformat()
    row = f"| {did} | {kind} | `{slug}` | {_cell(title)} | {_cell(reason)} | {today} | {revisit or '—'} |\n"
    text = read_text(p.decisions)
    if not text.endswith("\n"):
        text += "\n"
    write_text(p.decisions, text + row)
    return {"id": did, "type": kind, "slug": slug, "title": title, "reason": reason,
            "date": today, "revisit": revisit}
