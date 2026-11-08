---
name: run-session
description: Execute one Apex session packet end to end. Preflight, implement within the packet's target files, run its Definition-of-Done checks, mark it done, and commit atomically. Use after /apex:audit has produced packets.
argument-hint: "<session-id e.g. S-003> [--branch | --worktree]"
disable-model-invocation: true
allowed-tools: Bash(python3 *), Bash(git status *), Bash(git diff *), Bash(git add *), Bash(git commit *), Bash(git switch *), Read, Grep, Glob, Edit, Write
---

# /apex:run-session

APEX = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apex.py"` (always type the full
command). Arguments: `$ARGUMENTS`

## 0. Pick the session
Parse the session ID (`S-003`, `s3`, or `3` all work) and the flags `--branch`
and `--worktree`. With no ID, run `APEX session next` and use the first ready
session. Tell the owner which one you picked.

## 1. Preflight (stop on blockers)
Run `APEX session preflight <id>`:
- `ok: false`: explain the blockers (unfinished dependencies, already done) and stop.
- `stale_targets` not empty: target files changed since the packet was
  planned. Ask (AskUserQuestion) whether to continue anyway or re-plan with
  `/apex:audit quick`.
- `dirty_files` overlapping the packet's targets: stop and ask the owner to
  commit or stash first. Unrelated dirty files are fine; you'll commit only this
  session's files.
- If the packet says `model: opus` (Deep Architecture), mention once that it was
  planned for Opus. The owner can switch with `/model`. Then continue.

## 2. Branching
- **Default:** work and commit on the **current branch**, so sequential sessions
  build on each other with no stacked branches.
- `--branch`: `git switch -c apex/<id>-<slug>` first.
- `--worktree`: don't implement here. Print:
  ```bash
  git worktree add ../<repo>-<id> -b apex/<id>-<slug>
  cd ../<repo>-<id> && claude "/apex:run-session <id>"
  ```
  Then explain that parallel-safe sessions share no target files, so their branches
  merge cleanly. Stop.

## 3. Load context
Run `APEX session show <id>` and read the packet body (Goal, Context, Steps, DoD,
Risk). Read every `patterns` file to copy its conventions, then every `targets`
file that exists. Don't open `do_not_touch` paths for editing.

## 4. Implement
- `APEX session set-status <id> in_progress`
- Follow the Steps. Stay inside `targets`; adding or updating tests for them is fine.
  If the work truly needs another file, keep that change minimal and explain why
  in the final report.
- Never edit `.apex/` files directly; packet status changes go through APEX.
- Match the pattern files' style and the repo's lint and format rules.

## 5. Verify (Definition of Done)
- Run every `dod` command. If one fails, fix and re-run, up to **3 repair
  cycles**.
- Run `APEX session scope <id>`. Revert any `do_not_touch_violations`. For each
  `out_of_scope` file, revert it or justify it in the report.
- Walk through the packet's manual flow as far as you can (CLI, curl, or tests),
  and list the steps the owner should click through.

## 6. Close out
**If every DoD command passes:**
1. `APEX session set-status <id> done`
2. Stage only this session's files plus the packet file:
   `git add <changed target/test files> .apex/sessions/<packet file>`
3. `git commit -m "feat(apex): <id> <title>"`, with a 2-4 line body summarizing
   the change and the DoD evidence. Never push.

**If the DoD still fails after 3 cycles:** run
`APEX session set-status <id> blocked --notes "<one-line cause>"`, leave the
changes uncommitted for the owner to inspect, and explain what's blocking.

## 7. Report
Report in ≤12 lines: what changed (files), DoD results, the commit SHA (or
blocker), and the next ready sessions from `APEX session next`. If several are in
the parallel batch, note they can run at the same time in separate worktrees.
Suggest `/apex:audit quick` after a few sessions to re-score.
