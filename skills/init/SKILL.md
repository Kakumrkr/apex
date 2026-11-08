---
name: init
description: Set up Apex in this project. Interviews the owner to lock the Product North Star (audience, value proposition, competitors, non-goals) and confirms which non-destructive health checks Apex may run. Use once per project, before /apex:audit.
argument-hint: "[--force]"
disable-model-invocation: true
allowed-tools: Bash(python3 *), Read, Grep, Glob
---

# /apex:init

You are setting up **Apex**, a read-only project auditor, in the current project.
The CLI is `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apex.py"` (call it APEX below;
always type the full command, because shell variables don't persist between Bash
calls). Arguments: `$ARGUMENTS`

## 1. Check existing state
- If `.apex/north-star.md` exists and `--force` was **not** passed: show the
  current North Star and stop. Tell the owner that `/apex:init --force` replaces it
  (decisions, sessions, and history are kept).

## 2. Draft answers from the repo (≤6 tool calls)
Read README, `package.json`/`pyproject.toml`, and the main entry route to infer
the product name, what it does, and who it's for. Run `APEX detect` to get the
stack and proposed health checks.

## 3. Interview with AskUserQuestion (one call, 4 questions)
Offer 2-3 drafted options per question (your best guess first, labelled
"(Recommended)"). The owner can always pick "Other":
1. **Target audience:** who exactly is this for?
2. **Core value proposition:** the one outcome they get, ideally measurable.
3. **Top competitors:** 2-3 real products they'd otherwise use (multiSelect).
4. **Explicit non-goals:** what this product will deliberately *not* do (multiSelect).

Then make a second AskUserQuestion call (multiSelect) listing every detected health
check (`name: cmd`). Explain that Apex runs only the checks the owner approves,
with timeouts, and never `--fix`, installs, or migrations. Ask whether competitor web
research should be enabled (default yes).

## 4. Write it
Pipe a JSON spec to `APEX init` via a quoted heredoc (prevents shell expansion):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apex.py" init <<'APEX_JSON'
{"product": "…", "audience": "…", "value": "…",
 "competitors": ["…", "…"], "non_goals": ["…", "…"],
 "research": true,
 "health_checks": [{"name": "typecheck", "cmd": "…", "required": true, "timeout": 300}]}
APEX_JSON
```
Add `--force` after `init` only if the owner passed it. Include only the approved
health checks, keeping the detected `required`/`timeout` values.

## 5. Finish
Show the North Star and the approved checks. Then tell the owner:
- Commit `.apex/` so future audits can track progress. `.apex/research/` can be
  gitignored if competitor notes are private.
- Next step: `/apex:audit` (the first audit is a full scan; later audits are
  incremental).

_If AskUserQuestion isn't available (e.g. in Codex), ask the same questions in chat._
