"""`apex.py lint` — validates everything the auditor writes.

Errors block the auditor's SubagentStop (it must fix them); warnings don't.
"""
from __future__ import annotations

import glob
import json
import os
import re

from . import decisions as dec
from . import fm, gitutil, md, searchlog, sessions
from .paths import ApexPaths, read_text, rel
from .secrets import scan_text
from .state import (BIG_DELTA, BROKEN_BUILD_CAP, RUBRIC, SCORE_TOLERANCE, load_config,
                    load_json, load_state, weighted_score)

REQUIRED_SECTIONS = ("Scorecard", "Health Check", "Progress Since Last Audit", "First 60 Seconds",
                     "Parity Matrix", "Opportunities", "Session Plan")
VERDICTS = {"missing", "matches", "beats"}
ROADMAP_WARN_BYTES = 40_000
ROADMAP_MAX_BYTES = 80_000


class Report:
    def __init__(self, root: str):
        self.root = root
        self.items: list[dict] = []

    def add(self, level, code, msg, path=None):
        self.items.append({"level": level, "code": code, "message": msg,
                           "file": rel(self.root, path) if path else None})

    def error(self, code, msg, path=None):
        self.add("error", code, msg, path)

    def warn(self, code, msg, path=None):
        self.add("warn", code, msg, path)

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "error"]

    @property
    def warnings(self):
        return [i for i in self.items if i["level"] == "warn"]

    def text(self) -> str:
        if not self.items:
            return "apex lint: OK — no issues"
        lines = []
        for i in self.errors + self.warnings:
            where = f" [{i['file']}]" if i["file"] else ""
            lines.append(f"{i['level'].upper():5} {i['code']}{where}: {i['message']}")
        lines.append(f"apex lint: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return "\n".join(lines)


def _ids(cell: str) -> list[str]:
    return re.findall(r"\b(?:WF|DF)-\d{3,}\b", cell or "")


def _num(cell: str):
    m = re.search(r"-?\d+(?:\.\d+)?", cell or "")
    return float(m.group(0)) if m else None


def lint_scorecard(p: ApexPaths, r: Report, text: str, state: dict, audit_ctx: bool = False) -> dict | None:
    card, err = md.json_block(text, "scorecard")
    if err:
        r.error("scorecard", err, p.roadmap)
        return None
    for key in ("date", "mode", "overall", "dimensions", "health", "confidence", "research"):
        if key not in card:
            r.error("scorecard", f"scorecard is missing '{key}'", p.roadmap)
    dims = card.get("dimensions") or {}
    ok_dims = True
    for k in RUBRIC:
        v = dims.get(k)
        if not isinstance(v, (int, float)) or not 1.0 <= float(v) <= 10.0:
            r.error("scorecard", f"dimension '{k}' must be a number 1.0-10.0 (got {v!r})", p.roadmap)
            ok_dims = False
    for k in dims:
        if k not in RUBRIC:
            r.error("scorecard", f"unknown dimension '{k}' (allowed: {', '.join(RUBRIC)})", p.roadmap)
    overall = card.get("overall")
    if not isinstance(overall, (int, float)) or not 1.0 <= float(overall) <= 10.0:
        r.error("scorecard", f"overall must be 1.0-10.0 (got {overall!r})", p.roadmap)
        return card
    health = (card.get("health") or {}).get("status") if isinstance(card.get("health"), dict) else card.get("health")
    if health not in ("pass", "fail", "partial", "skipped"):
        r.error("scorecard", "health.status must be pass|fail|partial|skipped", p.roadmap)
    if card.get("mode") not in ("quick", "standard", "full"):
        r.error("scorecard", "mode must be quick|standard|full", p.roadmap)
    if card.get("confidence") not in ("low", "medium", "high"):
        r.error("scorecard", "confidence must be low|medium|high", p.roadmap)
    if card.get("research") not in ("full", "light", "cached", "skipped"):
        r.error("scorecard", "research must be full|light|cached|skipped", p.roadmap)
    if ok_dims:
        w = round(weighted_score(dims), 2)
        if health == "fail":
            if overall > BROKEN_BUILD_CAP:
                r.error("score-cap", f"required health checks fail, so overall must be <= {BROKEN_BUILD_CAP} (got {overall})", p.roadmap)
            if overall > w + SCORE_TOLERANCE:
                r.error("score-math", f"overall {overall} exceeds the weighted rubric score {w}", p.roadmap)
        elif abs(overall - w) > SCORE_TOLERANCE:
            r.error("score-math", f"overall {overall} must equal the weighted rubric score {w} (±{SCORE_TOLERANCE})", p.roadmap)
    # Cross-check against real health evidence.
    hj = load_json(p.health, {}) if os.path.exists(p.health) else None
    if hj and hj.get("status") and health in ("pass", "fail", "partial", "skipped"):
        head = gitutil.head_sha(p.root)
        if not head or hj.get("sha") == head:
            if hj["status"] != health:
                r.error("health-mismatch", f"scorecard says health '{health}' but .apex/.health.json recorded '{hj['status']}' — "
                        "report what the checks actually returned", p.roadmap)
        elif audit_ctx:
            r.warn("health-stale", ".apex/.health.json is from another commit; re-run `apex.py health`", p.health)
    elif audit_ctx and health in ("pass", "fail", "partial") and load_config(p).get("health_checks"):
        r.warn("health-evidence", "no .apex/.health.json evidence; run `apex.py health` during the audit", p.roadmap)
    prev = state.get("score")
    if isinstance(prev, (int, float)) and abs(float(overall) - prev) > BIG_DELTA:
        just = str(card.get("delta_justification") or "")
        if len(just.strip()) < 20:
            r.error("big-delta", f"score moved {prev} -> {overall} (> {BIG_DELTA}); add a 'delta_justification' "
                    "to the scorecard citing concrete evidence", p.roadmap)
    return card


def lint_parity(p: ApexPaths, r: Report, text: str, card: dict | None):
    sec = md.section(text, "Parity Matrix")
    rows = md.first_table(sec)
    research = (card or {}).get("research")
    if not rows:
        if research != "skipped":
            r.error("parity", "Parity Matrix needs a table (or set scorecard research to 'skipped')", p.roadmap)
        return
    head_comp = gitutil.show_head(p.root, p.competitors)
    if head_comp is None and gitutil.toplevel(p.root) is None:
        head_comp = read_text(p.competitors)  # no git: best effort
        r.warn("provenance", "no git repository: cached research can't be verified against history")
    known = searchlog.known(p, head_comp or "")
    for i, row in enumerate(rows, 1):
        verdict = md.col(row, "verdict", "status").strip().strip("*").lower()
        if verdict not in VERDICTS:
            r.error("parity", f"row {i}: verdict must be Missing|Matches|Beats (got {verdict!r})", p.roadmap)
        verified = md.col(row, "verified").strip().lower()
        if verified not in ("verified", "unverified"):
            r.error("parity", f"row {i}: Verified column must be 'verified' or 'unverified'", p.roadmap)
            continue
        if verified == "verified":
            urls = searchlog.extract(md.col(row, "source"))
            if not urls:
                r.error("provenance", f"row {i}: verified claims need a source URL", p.roadmap)
            for u in urls:
                if searchlog.normalize(u) not in known and searchlog.normalize(u, keep_query=False) not in known:
                    r.error("provenance", f"row {i}: {u} was never observed via WebSearch/WebFetch "
                            "(not in .apex/.search-log.json or committed research). Mark it 'unverified' "
                            "or fetch the page first.", p.roadmap)


def lint_opportunities(p: ApexPaths, r: Report, text: str, decisions: list[dict]) -> set[str]:
    rows = md.first_table(md.section(text, "Opportunities"))
    by_slug = {d["slug"]: d for d in decisions}
    by_id = {d["id"]: d for d in decisions}
    slugs = set()
    today = None
    for i, row in enumerate(rows, 1):
        slug = md.col(row, "slug").strip().strip("`")
        if not dec.SLUG_RE.match(slug or ""):
            r.error("opportunity", f"row {i}: slug must be kebab-case (got {slug!r})", p.roadmap)
            continue
        if slug in slugs:
            r.error("opportunity", f"duplicate opportunity slug '{slug}'", p.roadmap)
        slugs.add(slug)
        impact, effort = _num(md.col(row, "impact")), _num(md.col(row, "effort"))
        if impact is None or not 1 <= impact <= 5:
            r.error("opportunity", f"'{slug}': impact must be 1-5", p.roadmap)
        if effort is None or effort <= 0:
            r.error("opportunity", f"'{slug}': effort must be a positive number of sessions", p.roadmap)
        checked = _ids(md.col(row, "checked"))
        for cid in checked:
            if cid not in by_id:
                r.error("decision-ref", f"'{slug}' references {cid}, which is not in decisions.md", p.roadmap)
        hit = by_slug.get(slug)
        if hit and hit["type"] == "wont-fix":
            r.error("wont-fix", f"'{slug}' was rejected as {hit['id']} ({hit['reason']}). Remove it.", p.roadmap)
        elif hit and hit["type"] == "deferred":
            import datetime as _dt
            today = today or _dt.date.today().isoformat()
            if hit["id"] not in checked:
                r.error("deferred", f"'{slug}' matches deferred {hit['id']}; list {hit['id']} in its Checked column "
                        "to acknowledge the decision", p.roadmap)
            elif hit.get("revisit") and hit["revisit"] > today:
                r.error("deferred", f"'{slug}' ({hit['id']}) is deferred until {hit['revisit']}", p.roadmap)
    return slugs


def _cycle(graph: dict) -> list[str] | None:
    seen, stack = set(), []

    def visit(n):
        if n in stack:
            return stack[stack.index(n):] + [n]
        if n in seen:
            return None
        seen.add(n)
        stack.append(n)
        for m in graph.get(n, []):
            c = visit(m)
            if c:
                return c
        stack.pop()
        return None

    for n in graph:
        c = visit(n)
        if c:
            return c
    return None


def lint_sessions(p: ApexPaths, r: Report, opp_slugs: set[str]):
    pkts = sessions.load_all(p)
    ids = {}
    for s in pkts:
        path = s["_path"]
        missing = [k for k in sessions.REQUIRED if k not in s["_keys"]]
        if missing:
            r.error("packet", f"missing frontmatter: {', '.join(missing)}", path)
        sid = str(s.get("id") or "")
        if not sessions.ID_RE.match(sid):
            r.error("packet", f"id must look like S-001 (got {sid!r})", path)
        elif sid in ids:
            r.error("packet", f"duplicate id {sid} (also {rel(p.root, ids[sid])})", path)
        ids[sid] = path
        base = os.path.basename(path)
        if sid and s.get("slug") and base != f"{sid}-{s['slug']}.md":
            r.error("packet", f"filename must be {sid}-{s['slug']}.md", path)
        if s.get("status") not in sessions.STATUSES:
            r.error("packet", f"status must be one of {', '.join(sessions.STATUSES)}", path)
        if s.get("model") not in ("sonnet", "opus"):
            r.error("packet", "model must be 'sonnet' (standard execution) or 'opus' (deep architecture)", path)
        if s.get("parallel") not in ("safe", "depends"):
            r.error("packet", "parallel must be 'safe' or 'depends'", path)
        if s.get("parallel") == "depends" and not s.get("depends_on"):
            r.error("packet", "parallel: depends requires depends_on", path)
        n = len(s.get("targets") or [])
        if not 1 <= n <= sessions.MAX_TARGETS:
            r.error("packet", f"targets must list 1-{sessions.MAX_TARGETS} files (got {n}) — split the session", path)
        if not s.get("dod"):
            r.error("packet", "dod must list at least one verification command", path)
        est = s.get("estimate_hours")
        if not isinstance(est, (int, float)) or not 0.25 <= float(est) <= 2.5:
            r.error("packet", "estimate_hours must be between 0.25 and 2.5 (sessions are 1-2h)", path)
        heads = {md.norm_heading(h) for _, h in md.headings(s["_body"])}
        for sec in sessions.REQUIRED_SECTIONS:
            if not any(h.startswith(md.norm_heading(sec)) for h in heads):
                r.error("packet", f"missing '## {sec}' section", path)
        opp = s.get("opportunity")
        if opp and opp_slugs and opp not in opp_slugs and s.get("status") in ("todo", "in_progress"):
            r.warn("packet", f"opportunity '{opp}' is not in the roadmap's Opportunities table", path)
    idx = sessions.by_id(pkts)
    graph = {}
    for s in pkts:
        deps = s.get("depends_on") or []
        graph[s.get("id")] = deps
        for d in deps:
            if d == s.get("id"):
                r.error("packet", "a session cannot depend on itself", s["_path"])
            elif d not in idx:
                r.error("packet", f"depends_on {d} does not exist", s["_path"])
        if s.get("parallel") == "safe" and s.get("status") == "todo":
            unfinished = [d for d in deps if idx.get(d, {}).get("status") != "done"]
            if unfinished:
                r.error("packet", f"marked parallel-safe but depends on unfinished {', '.join(unfinished)}", s["_path"])
    cyc = _cycle(graph)
    if cyc:
        r.error("packet", "dependency cycle: " + " -> ".join(str(c) for c in cyc))
    active = [s for s in pkts if s.get("status") in ("todo", "in_progress") and s.get("parallel") == "safe"]
    for i, a in enumerate(active):
        for b in active[i + 1:]:
            overlap = set(a.get("targets") or []) & set(b.get("targets") or [])
            if overlap:
                r.error("parallel", f"{a.get('id')} and {b.get('id')} are both parallel-safe but share "
                        f"{', '.join(sorted(overlap))}; mark one 'depends'", a["_path"])
    # Done packets are immutable once committed.
    for s in pkts:
        committed = gitutil.show_head(p.root, s["_path"])
        if committed is None:
            continue
        head_meta, _ = fm.parse(committed)
        if head_meta.get("status") == "done" and committed != read_text(s["_path"]):
            r.error("immutable", f"{s.get('id')} is done in HEAD and must not be modified", s["_path"])
    top = gitutil.toplevel(p.root)
    if top:
        relsess = os.path.relpath(p.sessions_dir, top).replace(os.sep, "/")
        listing = gitutil._git(p.root, "ls-tree", "--name-only", "HEAD", relsess + "/") or ""
        for f in listing.splitlines():
            if not os.path.exists(os.path.join(top, f)):
                meta, _ = fm.parse(gitutil._git(p.root, "show", f"HEAD:{f}") or "")
                if meta.get("status") == "done":
                    r.error("immutable", f"done packet {f} was deleted")


def lint_secrets(p: ApexPaths, r: Report):
    files = [p.roadmap, p.north_star, p.decisions]
    files += glob.glob(os.path.join(p.sessions_dir, "*.md"))
    files += glob.glob(os.path.join(p.research_dir, "**", "*.*"), recursive=True)
    files += glob.glob(os.path.join(p.root, ".claude", "agent-memory", "apex*", "**", "*.md"), recursive=True)
    for f in files:
        for kind, line, snip in scan_text(read_text(f)):
            r.error("secret", f"possible {kind} at line {line} ({snip}); remove it — .apex/ is often committed", f)


def run(p: ApexPaths, require_roadmap: bool = False) -> Report:
    r = Report(p.root)
    if not p.exists():
        r.error("init", "no .apex/ directory — run /apex:init first")
        return r
    if not os.path.exists(p.north_star):
        r.error("init", "missing .apex/north-star.md — run /apex:init")
    for path in (p.config, p.state):
        if os.path.exists(path):
            try:
                json.loads(read_text(path))
            except json.JSONDecodeError as exc:
                r.error("json", f"invalid JSON: {exc.msg}", path)
    decisions = dec.load(p)
    seen = {}
    for d in decisions:
        if d["id"] in seen:
            r.error("decisions", f"duplicate decision id {d['id']}", p.decisions)
        if d["slug"] in seen.values():
            r.error("decisions", f"duplicate decision slug {d['slug']}", p.decisions)
        seen[d["id"]] = d["slug"]
    state = load_state(p)
    text = read_text(p.roadmap)
    opp_slugs: set[str] = set()
    if not text.strip():
        (r.error if require_roadmap else r.warn)("roadmap", "no .apex/roadmap.md yet — run /apex:audit", p.roadmap)
    else:
        size = len(text.encode("utf-8"))
        if size > ROADMAP_MAX_BYTES:
            r.error("size", f"roadmap is {size // 1000}KB; keep it under {ROADMAP_MAX_BYTES // 1000}KB "
                    "(history snapshots hold old detail)", p.roadmap)
        elif size > ROADMAP_WARN_BYTES:
            r.warn("size", f"roadmap is {size // 1000}KB; consider trimming", p.roadmap)
        heads = [md.norm_heading(h) for lvl, h in md.headings(text) if lvl == 2]
        for sec in REQUIRED_SECTIONS:
            if not any(h.startswith(md.norm_heading(sec)) for h in heads):
                r.error("roadmap", f"missing '## {sec}' section", p.roadmap)
        card = lint_scorecard(p, r, text, state, audit_ctx=require_roadmap)
        lint_parity(p, r, text, card)
        opp_slugs = lint_opportunities(p, r, text, decisions)
    lint_sessions(p, r, opp_slugs)
    lint_secrets(p, r)
    return r
