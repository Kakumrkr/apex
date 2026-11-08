"""Minimal YAML-frontmatter support (stdlib only).

Supports the subset Apex writes: `key: scalar`, inline lists `[a, b]`, and
block lists (`key:` followed by `  - item`). Values are strings, ints, floats,
booleans, null, or lists of those.
"""
from __future__ import annotations

import re

_FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)


def split(text: str) -> tuple[str | None, str]:
    m = _FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def _scalar(raw: str):
    v = raw.strip()
    if v == "" or v in ("~", "null", "None"):
        return None
    if (v[0] == v[-1]) and v[0] in "\"'" and len(v) >= 2:
        return v[1:-1]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def _inline_list(v: str) -> list:
    inner = v.strip()[1:-1].strip()
    if not inner:
        return []
    items, buf, quote = [], "", None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf += ch
        elif ch == ",":
            items.append(buf)
            buf = ""
        else:
            buf += ch
    items.append(buf)
    return [_scalar(i) for i in items if i.strip() != ""]


def parse(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body). Empty dict when there is none."""
    raw, body = split(text)
    if raw is None:
        return {}, body
    data: dict = {}
    key = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s+-\s*(.*)$", line)
        if m and key is not None:
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(_scalar(m.group(1)))
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        # strip trailing comments outside quotes
        if " #" in val and not val.strip().startswith(("'", '"')):
            val = val.split(" #", 1)[0]
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            data[key] = _inline_list(val)
        elif val == "":
            data[key] = None
        else:
            data[key] = _scalar(val)
    return data, body


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_fmt(i) for i in v) + "]"
    s = str(v)
    if s == "" or re.search(r"[:#\[\]{},]|^\s|\s$|^[-?|>!&*%@`'\"]", s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def set_fields(text: str, updates: dict) -> str:
    """Update/insert top-level scalar fields in place, preserving formatting."""
    raw, body = split(text)
    if raw is None:
        lines = [f"{k}: {_fmt(v)}" for k, v in updates.items()]
        return "---\n" + "\n".join(lines) + "\n---\n" + text
    lines = raw.splitlines()
    for k, v in updates.items():
        new = f"{k}: {_fmt(v)}".rstrip()
        for i, line in enumerate(lines):
            if re.match(rf"^{re.escape(k)}\s*:", line):
                # drop any block-list continuation lines
                j = i + 1
                while j < len(lines) and re.match(r"^\s+-", lines[j]):
                    j += 1
                lines[i:j] = [new]
                break
        else:
            lines.append(new)
    return "---\n" + "\n".join(lines) + "\n---\n" + body
