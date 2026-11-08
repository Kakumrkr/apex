"""Command-line interface for Apex. Run `apex.py --help`."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__, audit, decisions, hooks, lint, project, sessions
from .detect import detect
from .health import run as run_health
from .paths import paths_for
from .render import status_text, summary
from .state import migrate


def _out(obj, as_json: bool, text: str | None = None):
    if as_json:
        print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))
    else:
        print(text if text is not None else json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _session_public(s: dict) -> dict:
    return {k: v for k, v in s.items() if not k.startswith("_")}


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-dir", default=argparse.SUPPRESS,
                        help="project root (default: $CLAUDE_PROJECT_DIR or cwd)")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="machine-readable output")
    ap = argparse.ArgumentParser(prog="apex.py", parents=[common],
                                 description="Apex — deterministic bookkeeping for the Apex Claude Code plugin.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = lambda name, **kw: sub.add_parser(name, parents=[common], **kw)  # noqa: E731

    sp("version", help="print version")
    sp("status", help="dashboard: score, tier, trend, ready sessions")
    lp = sp("lint", help="validate .apex/ (scorecard math, provenance, packets, secrets)")
    lp.add_argument("--require-roadmap", action="store_true")
    sp("detect", help="detect stack and propose health checks")
    hp = sp("health", help="run configured health checks and record .apex/.health.json")
    hp.add_argument("--only", nargs="*", help="check names to run")
    ip = sp("init", help="create .apex/ and lock the North Star (JSON spec on stdin)")
    ip.add_argument("--force", action="store_true", help="replace an existing North Star")
    ip.add_argument("--stdin", action="store_true", help="read the JSON spec from stdin (default)")
    fp = sp("finalize-audit", help="lint, compute tier, update state.json, snapshot history")
    fp.add_argument("--date", help=argparse.SUPPRESS)
    sp("migrate", help="upgrade config/state schema")

    lk = sp("lock", help="audit lock")
    lk.add_argument("action", choices=["acquire", "release", "status"])
    lk.add_argument("--mode", default="standard")

    dp = sp("decision", help="won't-fix / deferred log")
    dsub = dp.add_subparsers(dest="action", required=True)
    da = dsub.add_parser("add", parents=[common])
    da.add_argument("--type", required=True, choices=sorted(decisions.TYPES))
    da.add_argument("--title", required=True)
    da.add_argument("--reason", required=True)
    da.add_argument("--slug")
    da.add_argument("--revisit", help="YYYY-MM-DD (deferred only)")
    dsub.add_parser("list", parents=[common])

    sess = sp("session", help="session packets")
    ssub = sess.add_subparsers(dest="action", required=True)
    ssub.add_parser("list", parents=[common])
    for name in ("show", "check", "scope", "preflight"):
        x = ssub.add_parser(name, parents=[common])
        x.add_argument("id")
    ss = ssub.add_parser("set-status", parents=[common])
    ss.add_argument("id")
    ss.add_argument("status", choices=sessions.STATUSES)
    ss.add_argument("--notes")
    ssub.add_parser("next", parents=[common])

    hk = sp("hook", help="hook entry point (reads event JSON on stdin)")
    hk.add_argument("name", choices=["guard-writes", "guard-reads", "guard-bash", "search-log",
                                     "subagent-stop", "session-start"])
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    as_json = getattr(args, "json", False)
    p = paths_for(getattr(args, "project_dir", None))
    try:
        if args.cmd == "version":
            _out({"version": __version__}, as_json, f"apex {__version__}")
        elif args.cmd == "hook":
            return hooks.run(args.name)
        elif args.cmd == "status":
            _out(summary(p), as_json, None if as_json else status_text(p))
        elif args.cmd == "lint":
            r = lint.run(p, require_roadmap=args.require_roadmap)
            _out({"errors": r.errors, "warnings": r.warnings}, as_json, r.text())
            return 1 if r.errors else 0
        elif args.cmd == "detect":
            _out(detect(p.root), True)
        elif args.cmd == "health":
            rep = run_health(p, args.only)
            if as_json:
                _out(rep, True)
            else:
                print(f"health: {rep['status']}  (sha {str(rep['sha'] or '')[:7]}{', dirty tree' if rep['dirty'] else ''})")
                for r in rep["results"]:
                    flag = "required" if r["required"] else "advisory"
                    print(f"  [{r['status'].upper():7}] {r['name']:<10} {r['duration_s']:>6}s  {flag:<8}  {r['cmd']}")
                    if r["status"] != "pass" and r["tail"]:
                        print("    " + "\n    ".join(r["tail"].splitlines()[-12:]))
            return 0
        elif args.cmd == "init":
            spec = json.loads(sys.stdin.read() or "{}")
            res = project.init(p, spec, force=args.force)
            _out(res, as_json, "Apex initialized:\n  " + "\n  ".join(res["created"]) +
                 ("\nNotes:\n  " + "\n  ".join(res["notes"]) if res["notes"] else "") +
                 "\nHealth checks:\n  " + ("\n  ".join(f"{c['name']}: {c['cmd']}" for c in res["config"]["health_checks"]) or "(none)"))
        elif args.cmd == "finalize-audit":
            res = audit.finalize(p, today=args.date)
            _out(res, True)
        elif args.cmd == "migrate":
            notes = migrate(p)
            _out(notes, as_json, "\n".join(notes) or "already up to date")
        elif args.cmd == "lock":
            if args.action == "acquire":
                _out(audit.lock_acquire(p, args.mode), True)
            elif args.action == "release":
                _out({"released": audit.lock_release(p)}, True)
            else:
                import os
                _out({"locked": os.path.exists(p.lock)}, True)
        elif args.cmd == "decision":
            if args.action == "add":
                _out(decisions.add(p, args.type, args.title, args.reason, args.slug, args.revisit), True)
            else:
                _out(decisions.load(p), True)
        elif args.cmd == "session":
            return _session(p, args, as_json)
    except (ValueError, RuntimeError, FileExistsError, json.JSONDecodeError) as exc:
        print(f"apex: {exc}", file=sys.stderr)
        return 2
    return 0


def _session(p, args, as_json) -> int:
    if args.action == "list":
        rows = [_session_public(s) for s in sessions.load_all(p)]
        if as_json:
            _out(rows, True)
        else:
            for s in rows:
                print(f"{s.get('id')}  {str(s.get('status')):<11} {str(s.get('model')):<6} "
                      f"{str(s.get('parallel')):<7} {s.get('title')}")
        return 0
    if args.action == "next":
        pk = sessions.load_all(p)
        _out({"ready": [s.get("id") for s in sessions.ready(pk)],
              "parallel_batch": [s.get("id") for s in sessions.parallel_batch(pk)]}, True)
        return 0
    if args.action == "set-status":
        s = sessions.set_status(p, args.id, args.status, args.notes)
        _out({"id": s["id"], "status": s["status"]}, True)
        return 0
    s = sessions.find(p, args.id)
    if not s:
        raise ValueError(f"session {args.id} not found")
    if args.action == "show":
        _out(dict(_session_public(s), body=s["_body"]), True)
    elif args.action == "check":
        _out({"id": s["id"], "stale_targets": sessions.staleness(p, s)}, True)
    elif args.action == "scope":
        rep = sessions.scope_report(p, s)
        _out(rep, True)
        return 1 if rep["do_not_touch_violations"] else 0
    elif args.action == "preflight":
        from . import gitutil
        idx = sessions.by_id(sessions.load_all(p))
        deps = {d: idx.get(d, {}).get("status", "missing") for d in s.get("depends_on") or []}
        blockers = []
        if s.get("status") in ("done", "dropped"):
            blockers.append(f"{s['id']} is already {s['status']}")
        unfinished = [d for d, st in deps.items() if st != "done"]
        if unfinished:
            blockers.append("unfinished dependencies: " + ", ".join(unfinished))
        dirty = [f for f in gitutil.dirty_files(p.root) if not f.startswith(".apex/")]
        _out({"id": s["id"], "title": s.get("title"), "status": s.get("status"), "model": s.get("model"),
              "dependencies": deps, "stale_targets": sessions.staleness(p, s),
              "dirty_files": dirty, "branch": gitutil.current_branch(p.root),
              "ok": not blockers, "blockers": blockers}, True)
        return 0 if not blockers else 1
    return 0
