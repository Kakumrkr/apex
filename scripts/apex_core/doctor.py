"""`apex.py doctor`: is the plugin wired correctly, are its guardrails live, is `.apex/` sound?

Read-only. Each check reports ok / warn / fail with a one-line fix. Exit code 1
when anything fails, so CI and `/apex:doctor` can gate on it.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import time

from . import SCHEMA_VERSION, __version__, gitutil
from .paths import ApexPaths, read_text

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APEX_PY = os.path.join(PLUGIN_ROOT, "scripts", "apex.py")
HOOKS = {  # hook name -> (event, matcher must mention, is a guardrail)
    "guard-writes": ("PreToolUse", "Write", True),
    "guard-bash": ("PreToolUse", "Bash", True),
    "guard-reads": ("PreToolUse", "Read", True),
    "search-log": ("PostToolUse", "WebFetch", True),
    "subagent-stop": ("SubagentStop", "apex-auditor", True),
    "session-start": ("SessionStart", "startup", False),
}
SKILLS = ("init", "audit", "run-session", "status", "defer", "doctor")
NORTH_STAR_SECTIONS = ("Product", "Target audience", "Core value proposition", "Top competitors",
                       "Explicit non-goals")
RUNTIME_FILES = (".apex/.lock", ".apex/.search-log.json", ".apex/.health.json")
SLOW_HOOK_MS = 400


def prompt_only() -> bool:
    """True for a Codex install (scripts copied without the Claude Code plugin manifest/hooks)."""
    return not os.path.isfile(os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json"))


class Checks:
    def __init__(self):
        self.items: list[dict] = []
        self.group = ""

    def section(self, name: str):
        self.group = name

    def add(self, status: str, name: str, detail: str = "", fix: str = ""):
        self.items.append({"group": self.group, "status": status, "check": name, "detail": detail, "fix": fix})

    def ok(self, name, detail=""):
        self.add("ok", name, detail)

    def warn(self, name, detail, fix=""):
        self.add("warn", name, detail, fix)

    def fail(self, name, detail, fix=""):
        self.add("fail", name, detail, fix)

    def count(self, status: str) -> int:
        return sum(1 for i in self.items if i["status"] == status)


def _load_json(path: str):
    try:
        return json.loads(read_text(path)), None
    except (OSError, ValueError) as exc:
        return None, str(exc)


# ---------------------------------------------------------------- environment
def check_environment(c: Checks) -> None:
    c.section("Environment")
    v = sys.version_info
    if v < (3, 9):
        c.fail("python", f"running on Python {v.major}.{v.minor}", "Apex needs Python 3.9+")
    else:
        c.ok("python", f"{v.major}.{v.minor}.{v.micro} ({sys.executable})")
    py3 = shutil.which("python3")
    if not py3:
        c.fail("python3 on PATH", "hooks run `python3`, which was not found",
               "install Python 3.9+ so `python3` is on PATH, or every guardrail silently fails open")
    else:
        try:
            out = subprocess.run([py3, "-I", "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
                                 capture_output=True, text=True, timeout=15).stdout.strip()
            major, minor = (int(x) for x in out.split("."))
            if (major, minor) < (3, 9):
                c.fail("python3 on PATH", f"{py3} is Python {out}", "point `python3` at Python 3.9+")
            else:
                c.ok("python3 on PATH", f"{py3} (Python {out})")
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            c.fail("python3 on PATH", f"{py3} did not run: {exc}", "fix the python3 install")
    git = shutil.which("git")
    c.ok("git", git) if git else c.fail("git", "not found on PATH", "install git; delta audits need it")


# --------------------------------------------------------------------- plugin
def check_plugin(c: Checks) -> None:
    c.section("Plugin")
    if prompt_only():
        c.warn("mode", f"prompt-only install at {PLUGIN_ROOT} (e.g. Codex): no hooks, so guardrails are "
               "advisory", "use Claude Code for enforced read-only audits; see docs/codex.md")
        return
    manifest, err = _load_json(os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json"))
    if manifest is None:
        c.fail("plugin.json", f"unreadable: {err}", "reinstall the plugin")
    elif manifest.get("name") != "apex":
        c.fail("plugin.json", f"name is {manifest.get('name')!r}, expected 'apex'")
    elif manifest.get("version") != __version__:
        c.warn("plugin.json", f"manifest v{manifest.get('version')} but scripts v{__version__}",
               "reinstall or update the plugin so both match")
    else:
        c.ok("plugin.json", f"apex v{__version__} at {PLUGIN_ROOT}")

    missing = [s for s in SKILLS if not os.path.isfile(os.path.join(PLUGIN_ROOT, "skills", s, "SKILL.md"))]
    if not os.path.isfile(os.path.join(PLUGIN_ROOT, "agents", "apex-auditor.md")):
        missing.append("agents/apex-auditor.md")
    c.fail("components", "missing: " + ", ".join(missing), "reinstall the plugin") if missing else \
        c.ok("components", f"{len(SKILLS)} skills + apex-auditor agent")

    hooks, err = _load_json(os.path.join(PLUGIN_ROOT, "hooks", "hooks.json"))
    if hooks is None:
        c.fail("hooks.json", f"unreadable: {err}", "reinstall the plugin; without it no guardrail runs")
        return
    found: dict[str, tuple[str, str, int | None]] = {}
    for event, groups in (hooks.get("hooks") or {}).items():
        for g in groups or []:
            for h in g.get("hooks") or []:
                cmd = h.get("command", "")
                for name in HOOKS:
                    if cmd.rstrip().endswith(f"hook {name}") and "${CLAUDE_PLUGIN_ROOT}/scripts/apex.py" in cmd:
                        found[name] = (event, g.get("matcher", ""), h.get("timeout"))
    problems = []
    for name, (event, needle, guardrail) in HOOKS.items():
        got = found.get(name)
        if not got:
            problems.append(f"{name} not registered")
        elif got[0] != event or needle not in got[1]:
            problems.append(f"{name} is on {got[0]}({got[1]}), expected {event}({needle}...)")
    if problems:
        c.fail("hooks.json", "; ".join(problems), "reinstall the plugin")
    else:
        c.ok("hooks.json", f"{len(found)} hooks registered on the expected events")

    unreadable = [f for f in (APEX_PY, os.path.join(PLUGIN_ROOT, "hooks", "hooks.json"))
                  if not os.access(f, os.R_OK)]
    c.fail("file permissions", "not readable: " + ", ".join(unreadable), "chmod a+r the plugin files") \
        if unreadable else c.ok("file permissions", "hook scripts readable (run via `python3 -I`, no exec bit needed)")


def _run_hook(name: str, event: dict) -> tuple[str, float]:
    t0 = time.perf_counter()
    out = subprocess.run([sys.executable, "-I", APEX_PY, "hook", name], input=json.dumps(event),
                         capture_output=True, text=True, timeout=30)
    return out.stdout.strip(), (time.perf_counter() - t0) * 1000


def _decision(stdout: str) -> str | None:
    try:
        return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]
    except (ValueError, KeyError, TypeError):
        return None


def check_hook_selftest(c: Checks, root: str) -> None:
    c.section("Guardrail self-test")
    auditor = {"cwd": root, "agent_type": "apex:apex-auditor", "hook_event_name": "PreToolUse"}
    cases = [
        ("auditor `git push` is denied", "guard-bash", dict(auditor, tool_name="Bash",
                                                         tool_input={"command": "git push"}), "deny"),
        ("auditor `git log` is allowed", "guard-bash", dict(auditor, tool_name="Bash",
                                                         tool_input={"command": "git log --oneline -5"}), "allow"),
        ("auditor write to src/ is denied", "guard-writes", dict(auditor, tool_name="Write",
                                                              tool_input={"file_path": "src/app.ts"}), "deny"),
        ("auditor read of .env is denied", "guard-reads", dict(auditor, tool_name="Read",
                                                            tool_input={"file_path": ".env"}), "deny"),
        ("north-star.md is locked for everyone", "guard-writes",
         {"cwd": root, "tool_name": "Edit", "tool_input": {"file_path": ".apex/north-star.md"}}, "deny"),
        ("your own Bash is untouched", "guard-bash",
         {"cwd": root, "tool_name": "Bash", "tool_input": {"command": "rm -rf build"}}, None),
    ]
    slowest = 0.0
    for label, hook, event, want in cases:
        try:
            out, ms = _run_hook(hook, event)
        except (OSError, subprocess.TimeoutExpired) as exc:
            c.fail(label, f"hook did not run: {exc}")
            continue
        slowest = max(slowest, ms)
        got = _decision(out) if out else None
        if got == want:
            c.ok(label, f"{ms:.0f} ms")
        else:
            c.fail(label, f"expected {want or 'no opinion'}, got {got or 'no opinion'} ({out[:120]!r})",
                   "report this at https://github.com/Kakumrkr/apex/issues")
    if slowest > SLOW_HOOK_MS:
        c.warn("hook latency", f"slowest hook took {slowest:.0f} ms", "a slow disk or antivirus can cause this")


def _settings_files(root: str) -> list[str]:
    home = os.path.expanduser("~")
    return [os.path.join(root, ".claude", "settings.json"), os.path.join(root, ".claude", "settings.local.json"),
            os.path.join(home, ".claude", "settings.json")]


def check_settings(c: Checks, root: str) -> None:
    c.section("Claude Code settings")
    seen_any = False
    for path in _settings_files(root):
        if not os.path.isfile(path):
            continue
        seen_any = True
        data, err = _load_json(path)
        short = path.replace(os.path.expanduser("~"), "~")
        if data is None:
            c.warn(short, f"invalid JSON ({err})", "Claude Code may ignore this file")
            continue
        if data.get("disableAllHooks") is True:
            c.fail(short, "disableAllHooks is true: every Apex guardrail is OFF",
                   "remove disableAllHooks, or audits run without the read-only lock")
        elif data.get("allowManagedHooksOnly") is True:
            c.fail(short, "allowManagedHooksOnly is true: plugin hooks are ignored",
                   "ask your admin to allow the Apex plugin's hooks")
        else:
            enabled = data.get("enabledPlugins") or {}
            off = [k for k, v in enabled.items() if k.split("@")[0] == "apex" and v is False]
            if off:
                c.warn(short, f"{', '.join(off)} is disabled here", "re-enable it with /plugin")
            else:
                c.ok(short, "hooks enabled")
    if not seen_any:
        c.ok("settings", "no settings files override hooks")


# -------------------------------------------------------------------- project
def check_project(c: Checks, p: ApexPaths) -> None:
    from . import decisions as dec
    from . import lint, sessions
    from .state import load_state

    c.section("Project (.apex/)")
    top = gitutil.toplevel(p.root)
    if not top:
        c.warn("git repository", f"{p.root} is not inside a git repo",
               "`git init`: delta audits, staleness checks and done-packet locks need git")
    else:
        c.ok("git repository", f"HEAD {gitutil.head_sha(p.root, short=True) or '(no commits yet)'}")
    if not p.exists():
        c.warn(".apex/", "not initialized in " + p.root, "run /apex:init")
        return

    text = read_text(p.north_star)
    if not text.strip():
        c.fail("north-star.md", "missing or empty", "run /apex:init")
    else:
        filled = {m.group(1).strip().lower() for m in re.finditer(r"^\*\*([^*:]+):\*\*[ \t]*\S", text, re.M)}
        absent = [s for s in NORTH_STAR_SECTIONS if s.lower() not in filled]
        c.warn("north-star.md", "missing or empty: " + ", ".join(absent), "re-run /apex:init --force") \
            if absent else c.ok("north-star.md", "all 5 fields filled")

    for label, path in (("config.json", p.config), ("state.json", p.state)):
        data, err = _load_json(path)
        if data is None:
            if os.path.exists(path):
                c.fail(label, f"invalid JSON: {err}", "restore it from git (`git checkout -- " + label + "`)")
            else:
                c.warn(label, "missing", "run /apex:init" if label == "config.json" else "created on first audit")
            continue
        ver = data.get("schema_version")
        if ver != SCHEMA_VERSION:
            c.warn(label, f"schema v{ver}, plugin expects v{SCHEMA_VERSION}", "run `apex.py migrate`")
        elif label == "config.json":
            checks = data.get("health_checks") or []
            bad = [x for x in checks if not (isinstance(x, dict) and x.get("name") and x.get("cmd"))]
            if bad:
                c.fail(label, f"{len(bad)} health check(s) lack a name or cmd", "fix config.json")
            elif not checks:
                c.warn(label, "no health checks configured: scores can't be backed by a real build",
                       "add checks to config.json or re-run /apex:init")
            else:
                req = sum(1 for x in checks if x.get("required"))
                c.ok(label, f"{len(checks)} health checks ({req} required)")
        else:
            c.ok(label, f"tier {data.get('tier') or '-'}, {len(data.get('history') or [])} audit(s)")

    state = load_state(p)
    sha = state.get("last_audit_sha")
    if sha and top:
        if gitutil.commit_exists(p.root, str(sha)):
            c.ok("last audited commit", f"{str(sha)[:7]} is reachable, so the next audit runs in delta mode")
        else:
            c.warn("last audited commit", f"{str(sha)[:7]} is not in this repo (rebased or shallow clone?)",
                   "the next audit falls back to a full scan; nothing to fix")
    hist_files = [f for f in os.listdir(p.history_dir) if re.search(r"-audit(-\d+)?\.md$", f)] if os.path.isdir(p.history_dir) else []
    n_hist = len(state.get("history") or [])
    if n_hist and len(hist_files) < n_hist:
        c.warn("history/", f"{n_hist} audits in state.json but {len(hist_files)} snapshot file(s)",
               "restore .apex/history/ from git")
    elif n_hist:
        c.ok("history/", f"{len(hist_files)} immutable snapshot(s)")

    ids = [d["id"] for d in dec.load(p)]
    c.ok("decisions.md", f"{len(ids)} decision(s)") if os.path.exists(p.decisions) else \
        c.warn("decisions.md", "missing", "run /apex:init")

    if top:
        unignored = [f for f in RUNTIME_FILES
                     if gitutil._git(p.root, "check-ignore", "-q", "--no-index", os.path.join(p.root, f)) is None]
        c.warn(".gitignore", "not ignored: " + ", ".join(unignored), "re-run /apex:init (it adds them)") \
            if unignored else c.ok(".gitignore", "runtime files ignored")
    if top:
        tracked = (gitutil._git(p.root, "ls-files", "--", *[os.path.join(p.root, f) for f in RUNTIME_FILES]) or "").split()
        if tracked:
            c.warn("runtime files", "committed to git: " + ", ".join(tracked),
                   "`git rm --cached` them; they are machine-local")

    if os.path.exists(p.lock):
        info, _ = _load_json(p.lock)
        try:
            age_h = (_dt.datetime.now() - _dt.datetime.fromisoformat((info or {}).get("started_at"))).total_seconds() / 3600
        except (TypeError, ValueError):
            age_h = 99.0
        if age_h > 3:
            c.warn("audit lock", f"stale lock from {age_h:.0f}h ago", "run `apex.py lock release`")
        else:
            c.ok("audit lock", f"an audit is running (started {age_h * 60:.0f} min ago)")

    packets = sessions.load_all(p)
    if packets:
        by = {}
        for s in packets:
            by[s.get("status")] = by.get(s.get("status"), 0) + 1
        c.ok("sessions", ", ".join(f"{v} {k}" for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))))

    rep = lint.run(p)
    if rep.errors:
        c.fail("lint", f"{len(rep.errors)} error(s), first: {rep.errors[0]['code']}: {rep.errors[0]['message'][:140]}",
               "run `apex.py lint` for the full list")
    elif rep.warnings:
        c.warn("lint", f"{len(rep.warnings)} warning(s), first: {rep.warnings[0]['message'][:140]}",
               "run `apex.py lint`")
    else:
        c.ok("lint", "no issues")


def run(p: ApexPaths, selftest: bool = True) -> Checks:
    c = Checks()
    check_environment(c)
    check_plugin(c)
    if not prompt_only():
        if selftest:
            check_hook_selftest(c, p.root)
        check_settings(c, p.root)
    check_project(c, p)
    return c


MARK = {"ok": "✓", "warn": "!", "fail": "✗"}


def text(c: Checks) -> str:
    out, group = [f"apex doctor · v{__version__}"], None
    for i in c.items:
        if i["group"] != group:
            group = i["group"]
            out.append(f"\n{group}")
        line = f"  {MARK[i['status']]} {i['check']}"
        if i["detail"]:
            line += f": {i['detail']}"
        out.append(line)
        if i["fix"] and i["status"] != "ok":
            out.append(f"      fix: {i['fix']}")
    fails, warns = c.count("fail"), c.count("warn")
    verdict = "healthy" if not fails and not warns else ("needs attention" if not fails else "broken")
    out.append(f"\n{len(c.items)} checks · {fails} failed · {warns} warning(s) · {verdict}")
    return "\n".join(out)
