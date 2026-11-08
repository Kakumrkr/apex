# Security model & threat model

Apex runs an autonomous agent with web access inside your repository. These are
the risks we design against and how each one is handled.

| Threat | Mitigation | Enforced by |
|---|---|---|
| Auditor edits source code | Write/Edit/NotebookEdit allowed only for `.apex/roadmap.md`, `.apex/sessions/S-###-*.md`, `.apex/research/*.md\|json`, and its agent memory (`*.md`). Paths are resolved (symlinks, `..`) before checking. | `guard-writes` hook |
| Auditor runs destructive shell commands | Bash is an **allowlist** of read-only commands. A quote-aware tokenizer splits the command (so `grep -E "a|b;c"` stays one argument) and checks every pipeline segment. Blocks file redirection, input redirection, `$VAR`/`${...}` expansion, command substitution, subshells, background jobs, `git` writes, installs, `--fix`/`--write`/`-u`, `python -c`, arbitrary scripts, and `npx` without `--no-install`. Only the plugin's own `apex.py` may run, and only its read-only subcommands. | `guard-bash` hook |
| Running the project's scripts (`npm run build`) | Only the exact commands you approved in `/apex:init` (stored in `config.json`), run by `apex.py health` with `shell=False`, `CI=1`, stdin closed, and per-check timeouts. | `apex.py health` + allowlist |
| Secret exfiltration | The auditor can't Read/Grep `.env*`, keys, `id_*`, `credentials*`, `.npmrc`, `*.tfvars`, … (`*.example` is allowed). Lint scans every `.apex/` file and agent memory for token patterns and blocks the audit if it finds one. | `guard-reads` hook + lint |
| Prompt injection via web pages or repo text | Treated as data (agent instructions). Even a successful injection can't write code, push, or run arbitrary commands, because of the guards above. | Hooks (defense in depth) |
| Hallucinated competitor claims | A `verified` parity row's URL must appear in `.apex/.search-log.json` (logged by a PostToolUse hook from real WebSearch/WebFetch results) or in **committed** `research/competitors.md`. | `search-log` hook + lint |
| Inflated or inconsistent scores | `overall` must equal the weighted rubric (±0.15). A failing required check caps it at 4.5. The scorecard's health status must match `.health.json`. A move of more than 1.5 needs a written justification. | lint (SubagentStop) |
| Tampering with your decisions | `north-star.md`, `decisions.md`, `state.json`, `history/`, and the evidence files are blocked from Write/Edit for **every** agent, including the main thread. Changes go through `apex.py`. | `guard-writes` hook |
| Re-litigating rejected ideas | Exact slug match against `decisions.md`: won't-fix slugs are rejected; deferred slugs need an explicit `Checked: DF-###` and an elapsed revisit date. | lint |
| Rewriting finished work | `done` packets that are committed can't change or be deleted. | lint |
| Python env hijacking | Hooks run `python3 -I` (ignores `PYTHONPATH`, user site, and `PYTHONSTARTUP`). | hooks.json |

## Failure policy
- Inside the auditor, a guard error **denies** (fail closed).
- Everywhere else, a guard error is silent (fail open), so an Apex bug never blocks your normal work.

## Known limits (please read)
- **Bash parsing is defense in depth, not a sandbox.** For strong isolation, enable Claude Code's sandbox mode as well.
- The guard denies recursive `grep`, `rg --hidden`/`--no-ignore`/`-u`, brace expansion, and unquoted globs that expand to a secret file (each glob is expanded against the working directory, tracking `cd`; patterns like `cat .e*` or `cat *.pem` are denied even when no such file exists yet), so the auditor uses `rg` (which skips hidden and gitignored files) or the guarded Grep tool. A secret file that is neither hidden nor gitignored, with an unremarkable name, can still be read. Lint catches secrets that end up in `.apex/`, not secrets read into context, so keep secrets gitignored.
- Run `/apex:doctor` after installing: it fires each guard with a real event and flags settings such as `disableAllHooks` that switch the guardrails off.
- Read-only checks may still write **caches** (`.mypy_cache`, `tsbuildinfo`, `__pycache__`, coverage). Apex never changes tracked source files.
- If `python3` isn't on `PATH`, hooks fail and Claude Code shows a hook error. The auditor can't work without `apex.py` anyway.
- In Codex (prompt-only mode) none of the hooks run.

Report vulnerabilities privately; see [SECURITY.md](../SECURITY.md).
