# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: [SemVer](https://semver.org/).

## [0.1.0] - 2026-11-08
### Hardened (pre-release review)
- Bash guard: a quote-aware tokenizer replaces `shlex` splitting, so `grep -E "a|b"`, `grep ";"`, and `rg 'x&&y'` are parsed correctly. It also denies `$VAR` expansion, brace expansion, input redirection, globs that could expand to secret files, recursive `grep`, and `rg --hidden`/`-u`, and checks `rev:path` arguments such as `HEAD:.env`.
- Frontmatter parser: colons in quoted and plain values, trailing `# comments` (including after quoted values), inline and block lists (indented or not), escapes, `|`/`>` block scalars, CRLF and BOM. `set_fields` keeps the file's line endings and round-trips every value.
- Search logger: scans every string in `tool_input` and `tool_response` (any shape, JSON inside strings, `\/` escapes, percent-encoded redirect targets, URLs nested in URLs, balanced parentheses).

### Added (pre-release review)
- `apex.py doctor` and `/apex:doctor`: environment, plugin wiring, a live guardrail self-test, settings that disable hooks, and `.apex/` integrity.
- Stack-specific inspection checklists (React, Next.js, Node APIs, FastAPI, Django, Python CLIs), exact complaint-mining queries for review sites, forums, and GitHub issues, tier exit criteria, and a micro-delighter catalogue with implementation patterns.
- `examples/generate_demo.py` rebuilds the zero-token demo with the real CLI.

### Fixed (found during end-to-end runs)
- Bash guard: `2>&1;` no longer trips the redirection check; read-only `sed -n <range>p` and `apex.py --help` are allowed.
- Auditor memory uses an explicit `MEMORY_FILE`, since plugin agents may not get an injected memory directory. The write guard accepts any `.claude/agent-memory/apex*/` directory.

### Added
- `apex-auditor` subagent (Opus, high effort, project memory, 50-turn budget, delta mode).
- Skills: `/apex:init`, `/apex:audit` (`quick` | `standard` | `full`), `/apex:run-session`, `/apex:status`, `/apex:defer`.
- `apex.py` stdlib CLI: init, detect (JS/TS + Python), health, status, lint, finalize-audit, lock, decision, session, migrate.
- Hooks: write/Bash/read guards for the auditor, protection of Apex-managed files for all agents, URL provenance logging, a lint gate on SubagentStop, and a SessionStart banner.
- 8-dimension weighted rubric with a broken-build cap, ±0.3 tier hysteresis, Mermaid score trend and session graph, and immutable history snapshots.
- End-to-end validation with headless Claude Code (audit → run-session → delta audit).
- Zero-token demo (`examples/demo-saas`), Codex installer (prompt-only mode), and docs.
