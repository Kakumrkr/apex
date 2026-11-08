"""PreToolUse guards. Each returns (decision, reason) or None for "no opinion".

decision is "allow" or "deny". "allow" is only ever returned for the Apex
auditor, and skips the permission prompt for provably read-only actions.
"""
from __future__ import annotations

import fnmatch
import os
import re
import shlex

from . import is_auditor
from .secrets import is_secret_path

APEX_PY = os.path.realpath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apex.py"))

# Files only apex.py may change (denied to Claude's Write/Edit for everyone).
MANAGED = (".apex/north-star.md", ".apex/decisions.md", ".apex/state.json",
           ".apex/.search-log.json", ".apex/.health.json", ".apex/.lock")
MANAGED_DIRS = (".apex/history/",)
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def _root(event: dict) -> str:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    return os.path.realpath(root)


def _rel(event: dict, path: str) -> tuple[str, bool]:
    """(project-relative posix path, inside_project)."""
    root = _root(event)
    base = event.get("cwd") or root
    full = os.path.realpath(os.path.join(base, os.path.expanduser(path)))
    relp = os.path.relpath(full, root).replace(os.sep, "/")
    return relp, not (relp == ".." or relp.startswith("../") or os.path.isabs(relp))


# ---------------------------------------------------------------- writes
def guard_writes(event: dict):
    if event.get("tool_name") not in WRITE_TOOLS:
        return None
    ti = event.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
    auditor = is_auditor(event.get("agent_type"))
    if not path:
        return ("deny", "Apex auditor: write without a file path") if auditor else None
    relp, inside = _rel(event, str(path))
    if inside and (relp in MANAGED or any(relp.startswith(d) for d in MANAGED_DIRS)):
        return ("deny", f"{relp} is managed by Apex and is append-only/immutable. "
                "Use /apex:init (North Star), /apex:defer (decisions), or apex.py — never edit it directly.")
    if not auditor:
        return None
    if inside and relp == ".apex/roadmap.md":
        return ("allow", "Apex auditor: roadmap update")
    if inside and re.fullmatch(r"\.apex/sessions/S-\d{3,}-[a-z0-9-]+\.md", relp):
        return ("allow", "Apex auditor: session packet")
    if inside and re.fullmatch(r"\.apex/research/[A-Za-z0-9._/-]+\.(md|json)", relp) and ".." not in relp:
        return ("allow", "Apex auditor: research cache")
    full = os.path.realpath(os.path.join(event.get("cwd") or _root(event), os.path.expanduser(str(path))))
    mem = re.search(r"[/\\]\.claude[/\\]agent-memory[/\\]([^/\\]+)[/\\]", full)
    if mem and mem.group(1).split(":")[-1].endswith("apex-auditor") and full.endswith(".md"):
        return ("allow", "Apex auditor: agent memory")
    return ("deny", f"Apex auditor is read-only for your code. It may only write .apex/roadmap.md, "
            f".apex/sessions/S-###-*.md, .apex/research/*.md|json and its agent memory — not {relp}.")


# ---------------------------------------------------------------- reads
def guard_reads(event: dict):
    if not is_auditor(event.get("agent_type")):
        return None
    ti = event.get("tool_input") or {}
    for key in ("file_path", "path", "glob", "pattern" if event.get("tool_name") == "Glob" else ""):
        val = ti.get(key) if key else None
        if not val:
            continue
        for part in re.split(r"[,{}\s]", str(val)):
            if part and is_secret_path(part):
                return ("deny", f"Apex auditor never reads secret files ({os.path.basename(part)}). "
                        "Audit config shape via *.example files or code that loads env vars instead.")
    return None


# ---------------------------------------------------------------- bash
SAFE_ENV = {"CI", "NODE_ENV", "FORCE_COLOR", "NO_COLOR", "TERM", "LANG", "LC_ALL",
            "PYTHONDONTWRITEBYTECODE", "TZ"}
SIMPLE_READONLY = {"ls", "cat", "head", "tail", "wc", "file", "stat", "tree", "pwd", "echo", "printf",
                   "grep", "egrep", "fgrep", "rg", "cut", "tr", "diff", "cmp", "comm", "du", "df",
                   "date", "basename", "dirname", "realpath", "readlink", "which", "true", "false",
                   "test", "jq", "nl", "column", "uname", "whoami", "sort", "uniq", "find", "fd"}
FIND_BAD = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
GIT_READ = {"status", "log", "diff", "show", "rev-parse", "ls-files", "ls-tree", "blame", "shortlog",
            "describe", "rev-list", "merge-base", "cat-file", "grep", "count-objects", "whatchanged",
            "branch", "tag", "remote", "config", "stash", "worktree", "reflog", "name-rev", "for-each-ref",
            "check-ignore", "version", "help"}
JS_RUNNERS = {"npx", "pnpm", "yarn", "bun", "bunx", "npm"}
PY_MODULES = {"pytest", "ruff", "mypy", "pyright", "pip", "pip_audit", "compileall", "unittest", "black", "isort"}
AUDITOR_APEX_SUBS = {("status",), ("lint",), ("health",), ("detect",), ("version",), ("session", "list"),
                     ("session", "show"), ("session", "check"), ("decision", "list")}
DEVNULL = re.compile(r"(?<!\S)(?:\d?>>?|&>)\s*/dev/null(?!\S)|(?<!\S)2>&1(?!\S)")


class Blocked(Exception):
    pass


def _flags(args, *bad):
    for a in args:
        for b in bad:
            if a == b or (b.startswith("--") and a.startswith(b + "=")):
                raise Blocked(f"flag {b} can modify files")


def _check_git(args):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        a = args[i]
        if a in ("-C",):
            i += 2
            continue
        if a in ("--no-pager", "--no-optional-locks", "-P") or a.startswith("--git-dir=") or a.startswith("--work-tree="):
            i += 1
            continue
        raise Blocked(f"git global option {a} is not allowed for the auditor")
    if i >= len(args):
        return
    sub, rest = args[i], args[i + 1:]
    if sub not in GIT_READ:
        raise Blocked(f"git {sub} is not a read-only git command")
    for a in rest:
        if a.startswith("--output") or a in ("--ext-diff", "-O", "--open-files-in-pager"):
            raise Blocked(f"git option {a} can write files or run programs")
    nonflags = [a for a in rest if not a.startswith("-")]
    if sub == "branch":
        bad = {"-d", "-D", "-m", "-M", "-c", "-C", "--delete", "--move", "--copy", "-f", "--force",
               "-u", "--set-upstream-to", "--unset-upstream", "--edit-description", "-t", "--track"}
        if any(a in bad or a.split("=")[0] in bad for a in rest) or (nonflags and not {"--list", "-l", "--contains", "--merged", "--no-merged", "--points-at"} & set(rest)):
            raise Blocked("git branch may only list branches")
    elif sub == "tag":
        if rest and not {"-l", "--list", "-n"} & set(rest) and not all(a.startswith("--sort") or a.startswith("--contains") for a in rest):
            raise Blocked("git tag may only list tags")
    elif sub == "remote":
        if nonflags and nonflags[0] not in ("get-url",):
            raise Blocked("git remote may only be listed (-v) or queried (get-url)")
    elif sub == "config":
        if not {"--get", "--get-all", "--list", "-l", "--get-regexp", "--show-origin"} & set(rest):
            raise Blocked("git config may only read values")
    elif sub in ("stash", "worktree", "reflog"):
        if (nonflags and nonflags[0] not in ("list", "show")) or (sub == "stash" and not nonflags):
            raise Blocked(f"git {sub} may only list/show")


def _check_js_tool(tool, args):
    tool = os.path.basename(tool)
    if tool == "tsc":
        if not ({"--noEmit", "-noEmit"} & set(args) or any(a in ("--version", "-v") for a in args)):
            raise Blocked("tsc must run with --noEmit")
        _flags(args, "--watch", "-w", "--outDir", "--outFile", "--declarationDir", "--generateTrace", "--init")
    elif tool == "eslint":
        _flags(args, "--fix", "--fix-type", "-o", "--output-file", "--init")
    elif tool == "prettier":
        if not {"--check", "-c", "--list-different", "-l"} & set(args):
            raise Blocked("prettier must run with --check")
        _flags(args, "--write", "-w")
    elif tool == "vitest":
        if not (args[:1] == ["run"] or "--run" in args or args[:1] == ["list"]):
            raise Blocked("vitest must run as `vitest run` (no watch mode)")
        _flags(args, "-u", "--update", "--watch", "-w", "--ui", "--outputFile")
    elif tool == "jest":
        _flags(args, "-u", "--updateSnapshot", "--watch", "--watchAll", "--outputFile")
    elif tool == "next":
        if args[:1] != ["lint"] and args[:1] != ["info"]:
            raise Blocked("only `next lint` / `next info` are allowed")
        _flags(args, "--fix")
    elif tool in ("knip", "depcheck", "madge", "license-checker"):
        _flags(args, "--fix", "--write", "-o", "--output", "--image")
    else:
        raise Blocked(f"{tool} is not on the auditor's read-only tool list")


def _check_py_module(mod, args):
    if mod not in PY_MODULES:
        raise Blocked(f"python -m {mod} is not on the auditor's read-only list")
    if mod == "ruff":
        _check_ruff(args)
    elif mod == "pip":
        if not args or args[0] not in ("list", "show", "freeze", "check", "--version"):
            raise Blocked("pip may only list/show/freeze/check")
    elif mod == "pip_audit":
        _flags(args, "--fix", "-o", "--output")
    elif mod in ("black", "isort"):
        if not {"--check", "--diff", "-c"} & set(args):
            raise Blocked(f"{mod} must run with --check")
    elif mod == "pytest":
        _flags(args, "--snapshot-update", "--basetemp", "--junitxml", "--resultlog")


def _check_ruff(args):
    if not args or args[0] not in ("check", "format", "--version", "version"):
        raise Blocked("ruff may only run `check` or `format --check`")
    if args[0] == "format" and not {"--check", "--diff"} & set(args):
        raise Blocked("ruff format must run with --check")
    _flags(args, "--fix", "--unsafe-fixes", "--fix-only", "-o", "--output-file", "--add-noqa")


def _check_apex(args):
    if not args or os.path.realpath(args[0]) != APEX_PY:
        raise Blocked("only the plugin's own apex.py may be executed")
    sub = tuple(a for a in args[1:] if not a.startswith("-"))[:2]
    if not any(sub[:len(s)] == s for s in AUDITOR_APEX_SUBS):
        raise Blocked(f"apex.py {' '.join(sub) or '(none)'} is reserved for the main thread "
                      "(the auditor may run: status, lint, health, detect, session list/show/check, decision list)")


def _check_python(args):
    while args and (args[0] in ("-B", "-I", "-q") or args[0].startswith(("-X", "-W"))):
        args = args[2:] if args[0] in ("-X", "-W") else args[1:]
    if not args:
        raise Blocked("interactive python is not allowed")
    if args[0] in ("--version", "-V"):
        return
    if args[0] == "-m" and len(args) > 1:
        return _check_py_module(args[1], args[2:])
    if args[0].endswith("apex.py"):
        return _check_apex(args)
    raise Blocked("python may only run `-m <read-only tool>` or Apex's apex.py (no -c / scripts)")


def _check_segment(argv: list[str]):
    while argv and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[0]):
        name, _, _val = argv[0].partition("=")
        if name not in SAFE_ENV:
            raise Blocked(f"environment assignment {name}= is not allowed")
        argv = argv[1:]
    if not argv:
        return
    for tok in argv:
        if is_secret_path(tok) or any(is_secret_path(p) for p in tok.split("=")[1:]):
            raise Blocked(f"{tok} looks like a secret file")
    prog, args = argv[0], argv[1:]
    if prog == "timeout":
        rest = [a for a in args if not a.startswith("-")]
        if len(rest) < 2:
            raise Blocked("timeout needs a duration and a command")
        return _check_segment(args[args.index(rest[0]) + 1:])
    if prog == "cd":
        return
    m = re.fullmatch(r"(?:\./)?node_modules/\.bin/([\w.-]+)", prog)
    if m:
        return _check_js_tool(m.group(1), args)
    m = re.fullmatch(r"(?:\./)?\.?venv/bin/([\w.-]+)", prog)
    if m:
        prog = m.group(1)
    elif "/" in prog or "\\" in prog:
        if prog.endswith("apex.py"):
            return _check_apex([prog] + args)
        raise Blocked(f"running {prog} directly is not allowed")
    if prog in SIMPLE_READONLY:
        if prog == "find" and FIND_BAD & set(args):
            raise Blocked("find with -exec/-delete/-fprint is not allowed")
        if prog == "sort":
            _flags(args, "-o", "--output")
        if prog == "uniq" and len([a for a in args if not a.startswith("-")]) > 1:
            raise Blocked("uniq with an output file is not allowed")
        if prog == "tree":
            _flags(args, "-o")
        if prog == "fd":
            _flags(args, "-x", "--exec", "-X", "--exec-batch")
        return
    if prog == "git":
        return _check_git(args)
    if re.fullmatch(r"python(3(\.\d+)?)?", prog):
        return _check_python(args)
    if prog in ("pytest", "mypy", "pyright"):
        return _check_py_module(prog, args)
    if prog == "ruff":
        return _check_ruff(args)
    if prog == "pip-audit":
        return _check_py_module("pip_audit", args)
    if prog in ("pip", "pip3"):
        return _check_py_module("pip", args)
    if prog in ("node", "deno", "bun") and args[:1] in (["--version"], ["-v"]):
        return
    if prog in JS_RUNNERS:
        return _check_js_runner(prog, args)
    if prog in ("tsc", "eslint", "prettier", "vitest", "jest", "next"):
        return _check_js_tool(prog, args)
    raise Blocked(f"`{prog}` is not on the auditor's read-only allowlist")


def _check_js_runner(prog, args):
    if not args:
        raise Blocked(f"bare {prog} is not allowed")
    if prog == "npx":
        if args[0] not in ("--no-install", "--no"):
            raise Blocked("use `npx --no-install <tool>` so nothing is downloaded")
        return _check_js_tool(args[1] if len(args) > 1 else "", args[2:])
    if prog == "bunx":
        raise Blocked("bunx may install packages; use node_modules/.bin/<tool>")
    if prog in ("pnpm", "yarn") and args[0] == "exec":
        return _check_js_tool(args[1] if len(args) > 1 else "", args[2:])
    if prog == "bun" and args[:2] == ["x", "--no-install"]:
        return _check_js_tool(args[2] if len(args) > 2 else "", args[3:])
    sub = args[0]
    if sub in ("--version", "-v"):
        return
    if sub in ("ls", "list", "outdated", "why", "explain", "view", "info"):
        return
    if sub == "audit":
        if "fix" in args or "--fix" in args:
            raise Blocked(f"{prog} audit fix modifies dependencies")
        return
    raise Blocked(f"`{prog} {sub}` is not allowed; scripts run only via configured health checks "
                  "(`apex.py health`)")


def check_command(cmd: str, allowed_exact: list[str] | tuple = ()) -> tuple[bool, str]:
    """Is `cmd` safe for the read-only auditor? Returns (ok, reason)."""
    cmd = (cmd or "").strip()
    if not cmd:
        return False, "empty command"
    if cmd in {c.strip() for c in allowed_exact}:
        return True, "configured health check"
    if "\n" in cmd or "\r" in cmd:
        return False, "multi-line commands are not allowed"
    if "`" in cmd or "$(" in cmd or "<(" in cmd or ">(" in cmd:
        return False, "command substitution is not allowed"
    cleaned = DEVNULL.sub(" ", cmd)
    try:
        lex = shlex.shlex(cleaned, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError as exc:
        return False, f"could not parse command ({exc})"
    segments, cur = [], []
    for tok in tokens:
        if tok and set(tok) <= set("();<>|&"):
            if tok in ("&&", "||", "|", ";"):
                segments.append(cur)
                cur = []
                continue
            if ">" in tok or "<" in tok:
                return False, "redirection to files is not allowed (only >/dev/null and 2>&1)"
            return False, f"shell operator {tok!r} is not allowed"
        cur.append(tok)
    segments.append(cur)
    try:
        for seg in segments:
            if not seg:
                raise Blocked("empty pipeline segment")
            _check_segment(seg)
    except Blocked as exc:
        return False, str(exc)
    return True, "read-only command"


def guard_bash(event: dict, allowed_exact=()):
    if not is_auditor(event.get("agent_type")):
        return None
    cmd = (event.get("tool_input") or {}).get("command", "")
    ok, reason = check_command(cmd, allowed_exact)
    if ok:
        return ("allow", f"Apex auditor: {reason}")
    return ("deny", f"Apex auditor is read-only — blocked: {reason}. "
            "Run configured checks with `apex.py health`; inspect code with Read/Grep/Glob.")
