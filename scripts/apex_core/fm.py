"""Minimal YAML-frontmatter support (stdlib only).

Parses the YAML subset Apex packets use (see `parse`). Values are strings,
ints, floats, booleans, null, or lists of those.
"""
from __future__ import annotations

import re

_FM_RE = re.compile(r"\A﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:(?:[ \t]+(.*)|[ \t]*)$")
_ITEM_RE = re.compile(r"^([ \t]*)-(?:[ \t]+(.*)|[ \t]*)$")
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", '"': '"', "\\": "\\", "/": "/"}


def split(text: str) -> tuple[str | None, str]:
    m = _FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def _typed(v: str):
    """Type a plain (unquoted) scalar."""
    v = v.strip()
    if v == "" or v in ("~", "null", "Null", "NULL", "None"):
        return None
    low = v.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if re.fullmatch(r"[-+]?\d+", v):
        return int(v)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+)", v):
        return float(v)
    return v


def _quoted(s: str, i: int) -> tuple[str, int]:
    """Parse a quoted scalar starting at s[i] (a quote). Returns (value, index after it)."""
    q, out, i = s[i], [], i + 1
    while i < len(s):
        ch = s[i]
        if q == "'" and ch == "'":
            if s.startswith("''", i):
                out.append("'")
                i += 2
                continue
            return "".join(out), i + 1
        if q == '"' and ch == "\\" and i + 1 < len(s):
            out.append(_ESCAPES.get(s[i + 1], "\\" + s[i + 1]))
            i += 2
            continue
        if q == '"' and ch == '"':
            return "".join(out), i + 1
        out.append(ch)
        i += 1
    raise ValueError(f"unterminated quote in {s!r}")


def _strip_comment(s: str) -> str:
    """Drop a trailing `# comment` (a '#' at the start or after whitespace)."""
    m = re.search(r"(?:^|[ \t])#", s)
    return s[:m.start()] if m else s


def _after(s: str, i: int, what: str):
    rest = s[i:].strip()
    if rest and not rest.startswith("#"):
        raise ValueError(f"unexpected text after {what}: {rest!r}")


def _value(raw: str):
    """Parse one value: quoted, inline list, or plain; trailing comments allowed."""
    s = raw.strip()
    if not s:
        return None
    if s[0] in "\"'":
        val, i = _quoted(s, 0)
        _after(s, i, "quoted value")
        return val
    if s[0] == "[":
        items, i, buf = [], 1, ""
        while i < len(s):
            ch = s[i]
            if ch in "\"'" and not buf.strip():
                val, i = _quoted(s, i)
                buf = None
                items.append(val)
                while i < len(s) and s[i] in " \t":
                    i += 1
                if i < len(s) and s[i] not in ",]":
                    raise ValueError(f"unexpected text after quoted list item in {s!r}")
                continue
            if ch in ",]":
                if buf is not None and buf.strip():
                    items.append(_typed(buf))
                buf = ""
                i += 1
                if ch == "]":
                    _after(s, i, "list")
                    return items
                continue
            buf = (buf or "") + ch
            i += 1
        raise ValueError(f"unterminated list in {s!r}")
    return _typed(_strip_comment(s))


def parse(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body). Empty dict when there is none.

    Supports the YAML subset Apex writes and humans commonly hand-edit:
    `key: scalar` (plain, "double" with escapes, or 'single' quoted, colons
    allowed), inline `[a, "b, c"]` and block (`- item`, indented or not)
    lists, `|`/`>` block scalars, `# comments` (full-line and trailing), and
    LF or CRLF line endings. Malformed lines are skipped, not fatal.
    """
    raw, body = split(text)
    if raw is None:
        return {}, body
    data: dict = {}
    key = None
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _ITEM_RE.match(line)
        if m and key is not None:
            if not isinstance(data.get(key), list):
                data[key] = []
            try:
                data[key].append(_value(m.group(2) or ""))
            except ValueError:
                data[key].append(_typed(_strip_comment(m.group(2) or "")))
            continue
        m = _KEY_RE.match(line)
        if not m:
            continue
        key, val = m.group(1), (m.group(2) or "")
        style = _strip_comment(val).strip()
        if style[:1] in ("|", ">") and re.fullmatch(r"[|>][-+]?", style):
            block = []
            while i < len(lines) and (not lines[i].strip() or lines[i][:1] in " \t"):
                block.append(lines[i].strip())
                i += 1
            while block and not block[-1]:
                block.pop()
            data[key] = ("\n" if style[0] == "|" else " ").join(block)
            continue
        try:
            data[key] = _value(val)
        except ValueError:
            data[key] = _typed(_strip_comment(val))
    return data, body


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_fmt(i) for i in v) + "]"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if (s == "" or _typed(s) != s or re.search(r"[:#\[\]{},\r\n\t\\]|^\s|\s$|^[-?|>!&*%@`'\"]", s)):
        return '"' + (s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                      .replace("\r", "\\r").replace("\t", "\\t")) + '"'
    return s


def set_fields(text: str, updates: dict) -> str:
    """Update/insert top-level scalar fields in place, preserving formatting."""
    nl = "\r\n" if "\r\n" in text[:4096] else "\n"
    bom = "\ufeff" if text.startswith("\ufeff") else ""
    raw, body = split(text)
    if raw is None:
        lines = [f"{k}: {_fmt(v)}" for k, v in updates.items()]
        return "---" + nl + nl.join(lines) + nl + "---" + nl + text
    lines = raw.splitlines()
    for k, v in updates.items():
        new = f"{k}: {_fmt(v)}".rstrip()
        for i, line in enumerate(lines):
            if re.match(rf"^{re.escape(k)}\s*:", line):
                # drop any block-list continuation lines
                j = i + 1
                while j < len(lines) and (_ITEM_RE.match(lines[j]) or
                                          (lines[j][:1] in " \t" and lines[j].strip())):
                    j += 1
                lines[i:j] = [new]
                break
        else:
            lines.append(new)
    return bom + "---" + nl + nl.join(lines) + nl + "---" + nl + body
