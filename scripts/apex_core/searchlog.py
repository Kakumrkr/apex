"""URL provenance: record URLs the auditor actually saw via WebSearch/WebFetch."""
from __future__ import annotations

import datetime as _dt
import json
import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from .paths import ApexPaths, read_text, write_text

# Universal scan: any http(s) URL, stopping at whitespace, quotes, angle brackets,
# closing parens/brackets, and backslashes (JSON escapes).
URL_RE = re.compile(r"https?://[^\s\"'<>)\]\\]+", re.I)
_TRAILING = ".,;:!?*_'\"}>|`("
MAX_ENTRIES = 3000


def normalize(url: str, keep_query: bool = True) -> str:
    url = url.strip().rstrip(_TRAILING)
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1].rstrip(_TRAILING)
    try:
        parts = urlsplit(url)
    except ValueError:
        return url.lower()
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/") or ""
    query = ""
    if keep_query and parts.query:
        q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith(("utm_", "ref", "fbclid", "gclid"))]
        query = urlencode(sorted(q))
    return urlunsplit(("https", host, path, query, ""))


def domain(url: str) -> str:
    return urlsplit(normalize(url)).hostname or ""


def _strings(obj, out: list, depth: int = 0) -> None:
    """Collect every string (keys and values) in a JSON-like structure."""
    if depth > 40:
        return
    if isinstance(obj, str):
        out.append(obj)
        t = obj.strip()
        if depth < 3 and t[:1] in "{[" and t[-1:] in "}]":
            try:  # a JSON document carried inside a string: scan it decoded too
                _strings(json.loads(t), out, depth + 1)
            except ValueError:
                pass
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _strings(k, out, depth + 1)
            _strings(v, out, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _strings(v, out, depth + 1)
    elif obj is not None:
        out.append(str(obj))


def extract(obj) -> list[str]:
    """Every URL anywhere in `obj`, whatever its shape.

    Scans each string in the structure, the structure serialized as JSON,
    and percent-decoded copies (redirect links such as `?url=https%3A%2F%2F...`).
    Order is preserved and duplicates removed.
    """
    texts: list[str] = []
    _strings(obj, texts)
    try:
        texts.append(json.dumps(obj, ensure_ascii=False, default=str).replace("\\/", "/"))
    except (TypeError, ValueError):
        pass
    seen, out = set(), []
    for text in texts:
        variants = [text]
        if "%3a" in text.lower():
            variants.append(unquote(text))
        if "\\u00" in text:
            variants.append(text.replace("\\u0026", "&").replace("\\u003d", "=").replace("\\u003D", "="))
        if "\\/" in text:
            variants.append(text.replace("\\/", "/"))
        for t in variants:
            for m in _START_RE.finditer(t):  # every http(s):// start, incl. URLs nested in URLs
                url = _scan_one(t, m.start())
                if url and url not in seen:
                    seen.add(url)
                    out.append(url)
    return out


_START_RE = re.compile(r"https?://", re.I)
_TAIL_RE = re.compile(r"[^\s\"'<>)\]\\]+")


def _scan_one(text: str, start: int) -> str | None:
    m = URL_RE.match(text, start)
    if not m:
        return None
    url, end = m.group(0), m.end()
    # Keep balanced parentheses, e.g. https://en.wikipedia.org/wiki/Foo_(bar)
    while end < len(text) and text[end] == ")" and url.count("(") > url.count(")"):
        url += ")"
        end += 1
        more = _TAIL_RE.match(text, end)
        if more:
            url += more.group(0)
            end = more.end()
    url = url.rstrip(_TRAILING)
    if url.count(")") > url.count("("):
        url = url.rstrip(")")
    if len(url) <= len("https://x") or "." not in url.split("//", 1)[1].split("/", 1)[0]:
        return None
    return url


def load(p: ApexPaths) -> dict:
    try:
        data = json.loads(read_text(p.search_log) or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def record(p: ApexPaths, urls: list[str], tool: str) -> int:
    if not p.exists() or not urls:
        return 0
    data = load(p)
    entries = data.setdefault("urls", {})
    now = _dt.datetime.now().replace(microsecond=0).isoformat()
    added = 0
    for u in urls:
        n = normalize(u)
        if n not in entries:
            entries[n] = {"domain": domain(u), "tool": tool, "first_seen": now}
            added += 1
    if len(entries) > MAX_ENTRIES:
        keep = sorted(entries.items(), key=lambda kv: kv[1].get("first_seen", ""))[-MAX_ENTRIES:]
        data["urls"] = dict(keep)
    write_text(p.search_log, json.dumps(data, indent=1) + "\n")
    return added


def known(p: ApexPaths, extra_text: str = "") -> set[str]:
    """Normalized URLs that count as observed: the search log + `extra_text`."""
    urls = set(load(p).get("urls", {}).keys())
    for u in extract(extra_text):
        urls.add(normalize(u))
    return urls | {normalize(u, keep_query=False) for u in urls}
