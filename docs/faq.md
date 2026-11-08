# FAQ

**How much does an audit cost?**
`full` and `standard` audits run the auditor on Opus at high effort with a 50-turn cap. Delta mode keeps
repeat audits much cheaper than the first one. `/apex:audit quick` uses Sonnet and skips web
research, which makes it good for weekly check-ins. `/apex:status` is nearly free.

**Will it change my code?**
Not during an audit. The auditor can write only `.apex/` audit files, and that's enforced by hooks, not
just the prompt. Code changes happen only when *you* run `/apex:run-session <id>`, which commits to your
current branch (no push).

**Which stacks are auto-detected?**
JavaScript/TypeScript (npm, pnpm, yarn, bun; tsc, eslint, vitest, jest, next) and Python (pytest,
ruff, mypy, pyright). For anything else, add commands to `.apex/config.json` → `health_checks`.

**Why can't I edit `north-star.md` or `decisions.md` with Claude?**
They're the owner's ground truth, so Claude's Write/Edit tools are blocked on them for every agent. Use
`/apex:init --force` or `/apex:defer`. You can still edit them in your own editor.

**Should I commit `.apex/`?**
Yes. Progress tracking, done-packet immutability, and research provenance all use git history. If your
competitor notes are private, gitignore `.apex/research/`.

**Can I run sessions in parallel?**
Yes, if they're tagged `Parallel-Safe`. The linter guarantees they share no target files. Use
`/apex:run-session S-008 --worktree` to get the git worktree commands.

**Does it work on Windows?**
The CLI is portable Python, but hooks call `python3`. Make sure `python3` is on `PATH` (e.g. via the
Python launcher alias) or run Claude Code in WSL.

**Can I change the rubric weights?**
Not in v0.1. Weights live in `scripts/apex_core/state.py` and the rubric reference. Configurable rubrics
are on the roadmap.
