---
name: doctor
description: Diagnose the Apex install for this project. Checks Python/git, plugin wiring, that the guardrail hooks actually fire (live self-test), Claude Code settings that could disable them, and .apex/ integrity (schema, North Star, state, history, lint). Read-only. Use when Apex behaves unexpectedly or after installing or upgrading.
model: sonnet
effort: low
allowed-tools: Bash(python3 *)
---

# /apex:doctor

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apex.py" doctor
```

Show the output to the owner verbatim in a code block. Then:
- If everything passed, say so in one line.
- For each `✗` (failed) line, explain in one sentence what it breaks and give
  the `fix:` step. Failures in "Guardrail self-test" or "Claude Code settings"
  mean audits are **not** read-only right now: say that plainly and suggest
  not running `/apex:audit` until they're fixed.
- Mention `!` warnings only briefly, unless the owner asks.

Don't modify anything. Offer to apply a fix only when it's a single command
the owner can approve (for example `apex.py migrate` or `apex.py lock release`).
