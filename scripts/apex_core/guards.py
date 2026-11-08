"""PreToolUse guards. Each returns (decision, reason) or None for "no opinion".

decision is "allow" or "deny". "allow" is only ever returned for the Apex
auditor, and skips the permission prompt for provably read-only actions.
"""
from __future__ import annotations

import fnmatch
import glob as _glob
import os
import re

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
                "Use /apex:init (North Star), /apex:defer (decisions), or apex.py. Never edit it directly.")
    if not auditor:
        return None
    if inside and relp == ".apex/roadmap.md":
        return ("allow", "Apex auditor: roadmap update")
    if inside and re.fullmatch(r"\.apex/sessions/S-\d{3,}-[a-z0-9-]+\.md", relp):
        return ("allow", "Apex auditor: session packet")
    if inside and re.fullmatch(r"\.apex/research/[A-Za-z0-9._/-]+\.(md|json)", relp) and ".." not in relp:
        return ("allow", "Apex auditor: research cache")
    full = os.path.realpath(os.path.join(event.get("cwd") or _root(event), os.path.expanduser(str(path))))
    # Claude Code names a plugin agent's memory dir after the plugin/agent (e.g. `apex`,
    # `apex-auditor`, `apex:apex-auditor`), so accept any `apex*` directory.
    mem = re.search(r"[/\\]\.claude[/\\]agent-memory[/\\]([^/\\]+)[/\\]", full)
    if mem and mem.group(1).startswith("apex") and full.endswith(".md"):
        return ("allow", "Apex auditor: agent memory")
    return ("deny", f"Apex auditor is read-only for your code. It may only write .apex/roadmap.md, "
            f".apex/sessions/S-###-*.md, .apex/research/*.md|json and its agent memory, not {relp}.")


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
# Sample names an unquoted glob must not be able to expand to (e.g. `cat .e*`, `cat *.pem`).
SECRET_SAMPLES = (".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "server.pem", "tls.key",
                  "credentials.json", "service-account.json", ".npmrc", ".netrc", ".pgpass", "secrets.yaml",
                  "prod.tfvars", "keystore.jks", "cert.p12")
GREP_RECURSIVE = {"-r", "-R", "--recursive", "--dereference-recursive"}
RG_UNHIDE = {"--hidden", "--no-ignore", "--no-ignore-dot", "--no-ignore-vcs", "--no-ignore-files", "-.", "-u",
             "-uu", "-uuu", "--unrestricted"}
SED_PRINT = re.compile(r"^(?:\d+|\$)(?:,(?:\d+|\$))?p$")


class Blocked(Exception):
    pass


class Word(str):
    """A shell word. `glob`/`brace` record unquoted `*?[` / `{` (expansion candidates)."""
    glob = False
    brace = False


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
    if not sub and {"-h", "--help"} & set(args[1:]):
        return
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


def _glob_reaches_secret(tok: str, cwd: str | None) -> bool:
    """Could this unquoted glob expand to a secret file?

    With a known working directory, expand it the way the shell would (Python's
    glob, like the shell, skips dotfiles unless the pattern starts with a dot).
    Patterns with a literal part (`*.pem`, `.e*`) are also checked against sample
    secret names, so they're denied even where no such file exists yet.
    """
    if cwd and os.path.isdir(cwd):
        path = os.path.expanduser(tok)
        try:
            matches = _glob.glob(path if os.path.isabs(path) else os.path.join(cwd, path))
        except (OSError, ValueError, RecursionError):
            return True
        if any(is_secret_path(m) for m in matches[:5000]):
            return True
    pat = os.path.basename(tok.rstrip("/")) or tok
    if not pat.strip("*?"):
        return False  # a bare `*`: only the filesystem expansion above can judge it
    return any(fnmatch.fnmatch(sample, pat) for sample in SECRET_SAMPLES
               if pat.startswith(".") or not sample.startswith("."))


def _check_segment(argv: list[str], cwd: str | None = None):
    while argv and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[0]):
        name, _, _val = argv[0].partition("=")
        if name not in SAFE_ENV:
            raise Blocked(f"environment assignment {name}= is not allowed")
        argv = argv[1:]
    if not argv:
        return
    for tok in argv:
        if any(is_secret_path(p) for p in re.split(r"[=:]", tok) if p):
            raise Blocked(f"{tok} looks like a secret file")
        if getattr(tok, "brace", False) and re.search(r"\{[^{}]*(?:,|\.\.)[^{}]*\}", tok):
            raise Blocked(f"brace expansion in {tok} is not allowed (list the paths explicitly)")
        if getattr(tok, "glob", False) and _glob_reaches_secret(tok, cwd):
            raise Blocked(f"the glob {tok} could match secret files; name the files explicitly")
    prog, args = argv[0], argv[1:]
    if prog == "timeout":
        rest = [a for a in args if not a.startswith("-")]
        if len(rest) < 2:
            raise Blocked("timeout needs a duration and a command")
        return _check_segment(args[args.index(rest[0]) + 1:], cwd)
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
    if prog == "sed":
        # Only `sed -n <range>p [files]`: sed scripts can otherwise write (w) or execute (e).
        if len(args) >= 2 and args[0] == "-n" and SED_PRINT.match(args[1]) and not any(a.startswith("-") for a in args[2:]):
            return
        raise Blocked("only `sed -n <start>,<end>p <file>` is allowed (use Read for files)")
    if prog in SIMPLE_READONLY:
        if prog in ("grep", "egrep", "fgrep") and any(
                a in GREP_RECURSIVE or re.fullmatch(r"-[A-Za-z]*[rR][A-Za-z]*", a) for a in args):
            raise Blocked("recursive grep can read .env and key files; use `rg` (skips hidden and "
                          "git-ignored files) or the Grep tool")
        if prog == "rg" and any(a in RG_UNHIDE or re.fullmatch(r"-[A-Za-z]*u[A-Za-z]*", a) for a in args):
            raise Blocked("rg --hidden/--no-ignore/-u can read .env and key files")
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


_OPERATORS = ("&&", "||", ";;", "|&", "&>", ">>", ">&", "<<", "<&", "<>", "|", ";", "&", ">", "<", "(", ")")
_SEPARATORS = {"&&", "||", "|", ";"}
_DOLLAR_EXPANSION = re.compile(r"[A-Za-z_{(0-9@*#?!$-]")


def tokenize(cmd: str) -> list[list[str]]:
    """Split a one-line shell command into pipeline segments of words.

    A small POSIX-style state machine: operators are recognised only outside
    quotes, so `grep -E "a|b;c"` stays one word. Raises Blocked for anything
    the auditor may not use (substitution, expansion, redirection to files,
    background jobs, subshells). `>/dev/null`, `2>/dev/null`, `&>/dev/null`
    and `N>&M` are accepted and dropped.
    """
    segments: list[list[str]] = [[]]
    word: list[str] = []
    in_word = quoted = globby = brace = False
    i, n = 0, len(cmd)

    def flush():
        nonlocal word, in_word, quoted, globby, brace
        if in_word:
            w = Word("".join(word))
            w.glob, w.brace = globby, brace
            segments[-1].append(w)
        word, in_word, quoted, globby, brace = [], False, False, False, False

    while i < n:
        ch = cmd[i]
        if ch == "'":
            j = cmd.find("'", i + 1)
            if j < 0:
                raise Blocked("could not parse command (unterminated single quote)")
            word.append(cmd[i + 1:j])
            in_word = quoted = True
            i = j + 1
            continue
        if ch == '"':
            i += 1
            while True:
                if i >= n:
                    raise Blocked("could not parse command (unterminated double quote)")
                c = cmd[i]
                if c == '"':
                    i += 1
                    break
                if c == "\\" and i + 1 < n and cmd[i + 1] in '"\\$`':
                    word.append(cmd[i + 1])
                    i += 2
                    continue
                if c == "`" or (c == "$" and i + 1 < n and _DOLLAR_EXPANSION.match(cmd[i + 1])):
                    raise Blocked("command substitution and variable expansion are not allowed")
                word.append(c)
                i += 1
            in_word = quoted = True
            continue
        if ch == "\\":
            if i + 1 < n:
                word.append(cmd[i + 1])
            in_word = quoted = True
            i += 2
            continue
        if ch == "`" or (ch == "$" and i + 1 < n and _DOLLAR_EXPANSION.match(cmd[i + 1])):
            raise Blocked("command substitution and variable expansion are not allowed")
        if ch in " \t":
            flush()
            i += 1
            continue
        op = next((o for o in _OPERATORS if cmd.startswith(o, i)), None)
        if op is None:
            word.append(ch)
            in_word = True
            globby = globby or ch in "*?["
            brace = brace or ch == "{"
            i += 1
            continue
        # Redirections: `N>`, `N>>`, `N>&M`, `&>`, `>`, `>>`. Only /dev/null and fd dups.
        fd = "".join(word) if in_word and not quoted and "".join(word).isdigit() else None
        if op in (">", ">>", ">&", "&>"):
            if fd is not None:
                word, in_word = [], False
            else:
                flush()
            i += len(op)
            if op == ">&" and fd is not None:
                m = re.match(r"\d+(?=$|[\s;&|])", cmd[i:])
                if not m:
                    raise Blocked("redirection to files is not allowed (only >/dev/null and 2>&1)")
                i += m.end()
                continue
            m = re.match(r"[ \t]*/dev/null(?=$|[\s;&|])", cmd[i:])
            if not m:
                raise Blocked("redirection to files is not allowed (only >/dev/null and 2>&1)")
            i += m.end()
            continue
        flush()
        if op in _SEPARATORS:
            segments.append([])
            i += len(op)
            continue
        if op in ("<", "<<", "<&", "<>"):
            raise Blocked("input redirection is not allowed (pass file names as arguments)")
        raise Blocked(f"shell operator {op!r} is not allowed")
    flush()
    return segments


def check_command(cmd: str, allowed_exact: list[str] | tuple = (), cwd: str | None = None) -> tuple[bool, str]:
    """Is `cmd` safe for the read-only auditor? Returns (ok, reason)."""
    cmd = (cmd or "").strip()
    if not cmd:
        return False, "empty command"
    if cmd in {c.strip() for c in allowed_exact}:
        return True, "configured health check"
    if "\n" in cmd or "\r" in cmd or "\0" in cmd:
        return False, "multi-line commands are not allowed"
    try:
        for seg in tokenize(cmd):
            if not seg:
                raise Blocked("empty pipeline segment")
            _check_segment(seg, cwd)
            if seg[0] == "cd" and cwd:  # later segments' globs expand relative to the new directory
                target = os.path.expanduser(seg[1]) if len(seg) > 1 else os.path.expanduser("~")
                cwd = os.path.normpath(os.path.join(cwd, target))
    except Blocked as exc:
        return False, str(exc)
    return True, "read-only command"


def guard_bash(event: dict, allowed_exact=()):
    if not is_auditor(event.get("agent_type")):
        return None
    cmd = (event.get("tool_input") or {}).get("command", "")
    ok, reason = check_command(cmd, allowed_exact, event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR"))
    if ok:
        return ("allow", f"Apex auditor: {reason}")
    return ("deny", f"Apex auditor is read-only. Blocked: {reason}. "
            "Run configured checks with `apex.py health`; inspect code with Read/Grep/Glob.")
