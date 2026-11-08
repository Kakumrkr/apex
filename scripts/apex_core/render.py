"""Human-facing output: status dashboard, session-start banner, Mermaid regions."""
from __future__ import annotations

import datetime as _dt
import os

from . import decisions as dec
from . import md, sessions
from .paths import ApexPaths, read_text
from .state import RUBRIC, RUBRIC_LABELS, TIER_NAMES, load_config, load_json, load_state

SPARK = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float]) -> str:
    return "".join(SPARK[min(7, max(0, int((v - 1) / 9 * 7 + 0.5)))] for v in values)


def bar(v: float, width: int = 10) -> str:
    filled = min(width, int(v / 10 * width + 0.5))
    return "█" * filled + "░" * (width - filled)


def days_ago(date: str | None) -> int | None:
    if not date:
        return None
    try:
        return (_dt.date.today() - _dt.date.fromisoformat(str(date)[:10])).days
    except ValueError:
        return None


def _project_name(p: ApexPaths) -> str:
    for line in read_text(p.north_star).splitlines():
        if line.lower().startswith("**product:**"):
            return line.split(":**", 1)[1].strip()
    return os.path.basename(p.root)


def summary(p: ApexPaths) -> dict:
    state, cfg = load_state(p), load_config(p)
    pkts = sessions.load_all(p)
    counts = {s: 0 for s in sessions.STATUSES}
    for s in pkts:
        counts[s.get("status")] = counts.get(s.get("status"), 0) + 1
    ready = sessions.ready(pkts)
    batch = sessions.parallel_batch(pkts)
    decs = dec.load(p)
    today = _dt.date.today().isoformat()
    card, _ = md.json_block(read_text(p.roadmap), "scorecard")
    hist = state.get("history") or []
    health = load_json(p.health, {}) if os.path.exists(p.health) else {}
    return {
        "project": _project_name(p),
        "initialized": os.path.exists(p.north_star),
        "score": state.get("score"),
        "tier": state.get("tier"),
        "tier_name": TIER_NAMES.get(state.get("tier")),
        "last_audit_date": state.get("last_audit_date"),
        "last_audit_sha": state.get("last_audit_sha"),
        "last_mode": state.get("last_mode"),
        "days_since_audit": days_ago(state.get("last_audit_date")),
        "stale_audit_days": cfg.get("stale_audit_days", 14),
        "history": [{"date": h.get("date"), "score": h.get("score"), "tier": h.get("tier")} for h in hist],
        "dimensions": (hist[-1].get("dimensions") if hist else None) or (card or {}).get("dimensions"),
        "health": {"status": health.get("status"), "sha": health.get("sha"),
                   "checks": [(c.get("name"), c.get("status")) for c in health.get("results", [])]},
        "sessions": counts,
        "in_progress": [{"id": s.get("id"), "title": s.get("title")} for s in pkts if s.get("status") == "in_progress"],
        "blocked": [{"id": s.get("id"), "title": s.get("title"), "notes": s.get("notes")} for s in pkts if s.get("status") == "blocked"],
        "ready": [{"id": s.get("id"), "title": s.get("title"), "model": s.get("model"),
                   "parallel": s.get("parallel"), "estimate_hours": s.get("estimate_hours")} for s in ready],
        "parallel_batch": [s.get("id") for s in batch],
        "decisions": {
            "wont_fix": sum(1 for d in decs if d["type"] == "wont-fix"),
            "deferred": sum(1 for d in decs if d["type"] == "deferred"),
            "due_for_revisit": [d["id"] for d in decs if d["type"] == "deferred" and d.get("revisit") and d["revisit"] <= today],
        },
    }


def status_text(p: ApexPaths) -> str:
    s = summary(p)
    if not s["initialized"]:
        return "Apex is not initialized here. Run /apex:init (Claude Code) to lock your Product North Star."
    out = [f"APEX · {s['project']}", ""]
    if s["score"] is None:
        out.append("Score   none yet (run /apex:audit)")
    else:
        hist = [h["score"] for h in s["history"] if isinstance(h.get("score"), (int, float))]
        delta = ""
        if len(hist) >= 2:
            d = hist[-1] - hist[-2]
            delta = f"  {'▲' if d >= 0 else '▼'} {d:+.1f} since {s['history'][-2]['date']}"
        out.append(f"Score   {s['score']:.1f} / 10{delta}")
        out.append(f"Tier    {s['tier_name']}")
        if hist:
            out.append(f"Trend   {sparkline(hist)}  ({len(hist)} audit{'s' if len(hist) != 1 else ''})")
        age = s["days_since_audit"]
        stale = "  ⚠ stale, consider /apex:audit" if age is not None and age > s["stale_audit_days"] else ""
        out.append(f"Audit   {s['last_audit_date']} ({age}d ago) · {s['last_mode']} · {str(s['last_audit_sha'] or '')[:7]}{stale}")
    h = s["health"]
    if h["status"]:
        marks = " ".join(f"{n} {'✓' if st == 'pass' else '✗'}" for n, st in h["checks"])
        out.append(f"Health  {h['status']} ({marks})")
    if s["dimensions"]:
        out += ["", "Dimensions"]
        for k in RUBRIC:
            v = s["dimensions"].get(k)
            if isinstance(v, (int, float)):
                out.append(f"  {RUBRIC_LABELS[k]:<30} {bar(v)} {v:.1f}")
    c = s["sessions"]
    out += ["", f"Sessions  {c['done']} done · {c['in_progress']} in progress · {c['todo']} todo · "
            f"{c['blocked']} blocked · {c['dropped']} dropped"]
    for x in s["in_progress"]:
        out.append(f"  ▶ in progress: {x['id']} {x['title']}")
    for x in s["blocked"]:
        out.append(f"  ■ blocked: {x['id']} {x['title']}" + (f" ({x['notes']})" if x.get("notes") else ""))
    if s["ready"]:
        out.append("  Ready now:")
        for x in s["ready"]:
            tag = "Parallel-Safe" if x["parallel"] == "safe" else "Sequential"
            out.append(f"    {x['id']}  {x['title']}  [{str(x['model']).title()} · {tag} · ~{x['estimate_hours']}h]")
        if len(s["parallel_batch"]) > 1:
            out.append(f"  Run in parallel (git worktrees): {', '.join(s['parallel_batch'])}")
        out.append(f"  Next: /apex:run-session {s['ready'][0]['id']}")
    d = s["decisions"]
    due = f" ({len(d['due_for_revisit'])} due for revisit: {', '.join(d['due_for_revisit'])})" if d["due_for_revisit"] else ""
    out += ["", f"Decisions  {d['wont_fix']} won't-fix · {d['deferred']} deferred{due}"]
    return "\n".join(out)


def banner(p: ApexPaths) -> str | None:
    if not os.path.exists(p.state) or not load_config(p).get("banner", True):
        return None
    s = summary(p)
    if s["score"] is None:
        return "Apex: initialized but not audited yet. Run /apex:audit."
    parts = [f"Apex {s['score']:.1f}/10 (Tier {s['tier']})"]
    age = s["days_since_audit"]
    if age is not None:
        parts.append(f"last audit {age}d ago" + (", consider /apex:audit" if age > s["stale_audit_days"] else ""))
    if s["in_progress"]:
        parts.append(f"in progress: {s['in_progress'][0]['id']}")
    elif s["ready"]:
        parts.append(f"next: {s['ready'][0]['id']} {s['ready'][0]['title']}")
    return " · ".join(parts) + " · /apex:status"


MERMAID_FLOW_INIT = ('%%{init: {"htmlLabels": false, '
                     '"flowchart": {"htmlLabels": false, "padding": 20}}}%%')


def _mq(s: str) -> str:
    return " ".join(str(s).split()).replace('"', "#quot;").replace("\\", "/")


def trend_region(history: list[dict]) -> str:
    hist = [h for h in history if isinstance(h.get("score"), (int, float))][-12:]
    if not hist:
        return "_No audits yet._"
    labels = ", ".join(f'"{str(h.get("date"))[5:10]}"' for h in hist)
    values = ", ".join(f"{h['score']:.1f}" for h in hist)
    return ("```mermaid\nxychart-beta\n    title \"Apex score over time\"\n"
            f"    x-axis [{labels}]\n    y-axis \"Score\" 0 --> 10\n    line [{values}]\n```")


def sessions_region(p: ApexPaths) -> str:
    allp = [s for s in sessions.load_all(p) if s.get("status") != "dropped"]
    done = [s for s in allp if s.get("status") == "done"]
    hidden = done[:-5]  # keep the roadmap lean: active packets + the 5 most recent done
    pkts = [s for s in allp if s not in hidden]
    if not pkts:
        return "_No session packets yet._"
    rows = ["| ID | Session | Model | Parallel | Depends on | Est. | Packet |",
            "|----|---------|-------|----------|------------|------|--------|"]
    for s in pkts:
        tag = "Parallel-Safe" if s.get("parallel") == "safe" else "Depends"
        deps = ", ".join(s.get("depends_on") or []) or "-"
        model = "Opus · Deep Architecture" if s.get("model") == "opus" else "Sonnet · Standard Execution"
        link = f"[{os.path.basename(s['_path'])}](sessions/{os.path.basename(s['_path'])})"
        rows.append(f"| {s.get('id')} | {s.get('title')} | {model} | {tag} | {deps} | {s.get('estimate_hours')}h | {link} |")
    # Native SVG labels: GitHub clips HTML (foreignObject) labels on the right edge.
    graph = ["```mermaid", MERMAID_FLOW_INIT, "flowchart LR"]
    for s in pkts:
        nid = str(s.get("id")).replace("-", "")
        graph.append(f'    {nid}["{_mq(s.get("id"))}\\n{_mq(s.get("title"))}"]:::{s.get("status")}')
    for s in pkts:
        for d in s.get("depends_on") or []:
            graph.append(f"    {str(d).replace('-', '')} --> {str(s.get('id')).replace('-', '')}")
    graph += ["    classDef done fill:#d1fae5,stroke:#059669,color:#064e3b",
              "    classDef in_progress fill:#dbeafe,stroke:#2563eb,color:#1e3a8a",
              "    classDef blocked fill:#fee2e2,stroke:#dc2626,color:#7f1d1d",
              "    classDef todo fill:#f3f4f6,stroke:#6b7280,color:#111827", "```"]
    note = "_Statuses live in each packet's frontmatter; run `/apex:status` for live progress._"
    if hidden:
        note = f"_{len(hidden)} older completed session(s) omitted; see `.apex/sessions/`._ " + note
    return "\n".join(rows) + "\n\n" + "\n".join(graph) + "\n\n" + note
