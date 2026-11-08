---
name: audit
description: Run an Apex audit — measure progress since the last audit, verify health with real checks, score the project 1.0-10.0 against an evidence rubric, benchmark competitors, and refresh .apex/roadmap.md plus 1-2 hour session packets. Then triage the proposals with the owner.
argument-hint: "[quick|standard|full] [--refresh]"
disable-model-invocation: true
allowed-tools: Bash(python3 *), Bash(git rev-parse *), Bash(git status *), Read, Grep, Glob
---

# /apex:audit — orchestrate an audit, then triage with the owner

You are the **orchestrator** in the main conversation. The heavy, read-only audit
runs in the `apex-auditor` subagent. Your jobs are setup, delegation, finalization,
and interactive triage (the subagent can't ask questions; you can).

APEX = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apex.py"` (always type the full
command). Arguments: `$ARGUMENTS`

## 1. Preconditions
- If `.apex/north-star.md` is missing, tell the owner to run `/apex:init` and stop.
- Run `APEX status --json` and `APEX migrate`.
- **Mode:** use the explicit argument if given. Otherwise use `full` when there's no
  `last_audit_sha` (first audit), else `standard`.
  - `quick`: no web research, delta code review, and the auditor runs on Sonnet (cheap check-in).
  - `standard`: delta code review (80% on changes since the last audit), cached research refreshed when stale.
  - `full`: complete codebase map plus fresh research. `--refresh` forces new research in any mode.
- Run `APEX lock acquire --mode <mode>`. If it fails because an audit is already
  running, stop and show the message.

## 2. Delegate to the auditor
Call the **Agent** tool with `subagent_type` set to the Apex auditor (it appears
as `apex-auditor` or `apex:apex-auditor` in your agent list). For `quick`
mode, also pass `model: "sonnet"`. Prompt it with:

```
Run an Apex audit.
APEX_PY=${CLAUDE_PLUGIN_ROOT}/scripts/apex.py
REFS=${CLAUDE_PLUGIN_ROOT}/skills/audit/references
MODE=<mode>   REFRESH_RESEARCH=<true|false>
LAST_SHA=<last_audit_sha or none>   LAST_AUDIT_DATE=<date or none>
TIER=<tier or none>   PREVIOUS_SCORE=<score or none>   TODAY=<YYYY-MM-DD>
Follow your protocol. Use `python3 $APEX_PY …` for CLI calls (expand the path).
Return the ≤15-line summary when lint passes.
```

## 3. Finalize (deterministic)
- Run `APEX lint --require-roadmap`. If it fails, send the errors back to the
  auditor **once** (SendMessage to the same agent, or a new Agent call with the
  lint output). Never fix the roadmap yourself — that would bypass the
  evidence checks. If it still fails, run `APEX lock release`, report, and stop.
- Run `APEX finalize-audit`. It computes the tier (with hysteresis), updates
  `state.json`, regenerates the trend and session regions, writes the immutable
  `.apex/history/` snapshot, and releases the lock.

## 4. Triage with the owner (AskUserQuestion)
Show a compact report: score and delta, tier (call out changes), health, the 3
biggest findings, and the new session packets (ID · title · model · parallel tag ·
estimate).

Then ask, in one AskUserQuestion call (multiSelect): **which proposed sessions
should stay in the plan?** Each new packet is an option. For every packet the
owner deselects, ask whether it's **Won't fix** (never suggest again) or
**Deferred** (with an optional revisit date), plus a one-line reason. Then:
- `APEX decision add --type wont-fix|deferred --slug <opportunity slug> --title "…" --reason "…" [--revisit YYYY-MM-DD]`
- `APEX session set-status <id> dropped --notes "<WF/DF id>"`

Skip triage if the owner said to accept everything.

## 5. Hand-off
- `APEX status` (show the dashboard).
- Suggest committing `.apex/` (e.g. `chore(apex): audit YYYY-MM-DD — score X.X`).
  Don't commit unless the owner asks.
- Name the next command: `/apex:run-session <first ready id>`. If several
  parallel-safe sessions are ready, mention running them in separate git worktrees.

## Other agents (e.g. Codex)
If you have no subagent tool, perform the protocol in
`${CLAUDE_PLUGIN_ROOT}/agents/apex-auditor.md` yourself, with the same inputs and
rules. No hooks enforce them there, so be strict: write only the `.apex/`
files it names. If AskUserQuestion isn't available, ask the triage questions in chat.

## Failure handling
On any error after `lock acquire`, run `APEX lock release` before stopping.
