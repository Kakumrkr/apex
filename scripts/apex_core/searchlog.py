"""URL provenance: record URLs the auditor actually saw via WebSearch/WebFetch."""
from __future__ import annotations

import datetime as _dt
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .paths import ApexPaths, read_text, write_text

URL_RE = re.compile(r"https?://[^\s\"'<>()\[\]{}|\\^`]+", re.I)
MAX_ENTRIES = 3000


def normalize(url: str, keep_query: bool = True) -> str:
    url = url.strip().rstrip(".,;:!?*_")
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


def extract(obj) -> list[str]:
    blob = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return [m.group(0) for m in URL_RE.finditer(blob.replace("\\/", "/"))]


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
