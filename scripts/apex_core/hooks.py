"""Hook entry points (`apex.py hook <name>`), wired in hooks/hooks.json.

Failure policy: if anything goes wrong *inside the auditor*, deny (fail
closed). For every other agent/session, stay silent (fail open) so a bug in
Apex can never block a user's normal work.
"""
from __future__ import annotations

import json
import sys

from . import is_auditor
import os

from .paths import paths_for


def _emit_pre(decision: str, reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": decision,
                                             "permissionDecisionReason": reason}}))


def _read_event() -> dict:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _paths(event: dict):
    return paths_for(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd"))


def run(name: str) -> int:
    event = _read_event()
    auditor = is_auditor(event.get("agent_type"))
    # Non-auditor Bash/Read/PostToolUse calls never need the heavy modules.
    if not auditor and name in ("guard-bash", "guard-reads", "search-log", "subagent-stop"):
        return 0
    try:
        from . import guards, lint, searchlog  # noqa: F401  (lazy for speed)
        from .render import banner
        from .state import load_config
        if name == "guard-writes":
            res = guards.guard_writes(event)
        elif name == "guard-reads":
            res = guards.guard_reads(event)
        elif name == "guard-bash":
            if not auditor:
                return 0
            cfg = load_config(_paths(event))
            exact = [c.get("cmd", "") for c in cfg.get("health_checks") or []]
            res = guards.guard_bash(event, exact)
        elif name == "search-log":
            if auditor and event.get("tool_name") in ("WebSearch", "WebFetch"):
                p = _paths(event)
                payload = {k: event.get(k) for k in
                           ("tool_input", "tool_response", "tool_result", "tool_output", "output")
                           if event.get(k) is not None}
                urls = searchlog.extract(payload)
                searchlog.record(p, urls, event.get("tool_name"))
            return 0
        elif name == "subagent-stop":
            if not auditor:
                return 0
            report = lint.run(_paths(event), require_roadmap=True)
            if report.errors:
                msgs = "\n".join(f"- {e['code']}{' [' + e['file'] + ']' if e['file'] else ''}: {e['message']}"
                                 for e in report.errors[:25])
                print(json.dumps({"decision": "block", "reason":
                                  "Apex lint found problems in your audit output. Fix them, re-run "
                                  "`apex.py lint`, then finish:\n" + msgs}))
            return 0
        elif name == "session-start":
            line = banner(_paths(event))
            if line:
                print(line)
            return 0
        else:
            print(f"unknown hook {name}", file=sys.stderr)
            return 0
    except Exception as exc:  # noqa: BLE001 - hooks must never crash the session
        if auditor and name.startswith("guard-"):
            _emit_pre("deny", f"Apex guard error ({type(exc).__name__}: {exc}); denying to stay safe.")
        else:
            print(f"apex hook {name}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0
    if res:
        _emit_pre(*res)
    return 0
