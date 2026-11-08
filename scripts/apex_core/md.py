"""Markdown helpers: sections, pipe tables, JSON comment blocks, managed regions."""
from __future__ import annotations

import json
import re

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def headings(text: str) -> list[tuple[int, str]]:
    out, fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        m = None if fence else _HEADING.match(line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip()))
    return out


def norm_heading(h: str) -> str:
    h = re.sub(r"[^\w\s-]", "", h).strip().lower()
    return re.sub(r"\s+", " ", h)


def section(text: str, name: str, level: int = 2) -> str | None:
    """Body of the first heading at `level` whose text starts with `name`."""
    lines = text.splitlines()
    want = norm_heading(name)
    start, fence = None, False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
        if fence:
            continue
        m = _HEADING.match(line)
        if not m:
            continue
        lvl = len(m.group(1))
        if start is None:
            if lvl == level and norm_heading(m.group(2)).startswith(want):
                start = i + 1
        elif lvl <= level:
            return "\n".join(lines[start:i])
    return "\n".join(lines[start:]) if start is not None else None


def _cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    parts, buf, esc = [], "", False
    for ch in s:
        if esc:
            buf += ch
            esc = False
        elif ch == "\\":
            esc = True
            buf += ch
        elif ch == "|":
            parts.append(buf)
            buf = ""
        else:
            buf += ch
    parts.append(buf)
    return [p.strip().replace("\\|", "|") for p in parts]


def tables(text: str) -> list[list[dict]]:
    """All pipe tables in `text` as lists of {header: cell} rows."""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines) - 1:
        if lines[i].strip().startswith("|") and re.match(
            r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", lines[i + 1]
        ):
            header = [h.lower() for h in _cells(lines[i])]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = _cells(lines[j])
                cells += [""] * (len(header) - len(cells))
                rows.append(dict(zip(header, cells)))
                j += 1
            out.append(rows)
            i = j
        else:
            i += 1
    return out


def first_table(text: str | None) -> list[dict]:
    if not text:
        return []
    t = tables(text)
    return t[0] if t else []


def col(row: dict, *names: str) -> str:
    """Case-insensitive column lookup by prefix (e.g. 'verdict' matches 'verdict (missing/...)')."""
    for n in names:
        n = n.lower()
        for k, v in row.items():
            if k == n or k.startswith(n):
                return v
    return ""


def json_block(text: str, tag: str):
    """Parse `<!-- apex:<tag> {json} -->`. Returns (obj, error)."""
    m = re.search(rf"<!--\s*apex:{re.escape(tag)}\s*(\{{.*?\}})\s*-->", text, re.S)
    if not m:
        return None, f"missing <!-- apex:{tag} {{...}} --> block"
    try:
        return json.loads(m.group(1)), None
    except json.JSONDecodeError as exc:
        return None, f"apex:{tag} block is not valid JSON ({exc.msg} at line {exc.lineno})"


def replace_region(text: str, name: str, content: str) -> str:
    """Replace (or append) a managed `<!-- apex:NAME:start -->...<!-- apex:NAME:end -->` region."""
    start, end = f"<!-- apex:{name}:start -->", f"<!-- apex:{name}:end -->"
    block = f"{start}\n{content.rstrip()}\n{end}"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pat.search(text):
        return pat.sub(lambda _m: block, text, count=1)
    return text.rstrip() + "\n\n" + block + "\n"
