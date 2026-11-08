---
name: status
description: Show the Apex dashboard for this project, with score and trend, tier, health, dimension bars, sessions ready to run (and which can run in parallel), and the decisions log. Cheap, read-only, and needs no web access.
model: sonnet
effort: low
allowed-tools: Bash(python3 *)
---

# /apex:status

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apex.py" status
```

Show the output to the owner verbatim in a code block. Then add at most two
lines of advice:
- If it says Apex isn't initialized, suggest `/apex:init`.
- If there's no audit yet or the audit is stale, suggest `/apex:audit` (or
  `/apex:audit quick` for a cheap check-in).
- If a session is ready, suggest `/apex:run-session <id>`.
- If a session is blocked, offer to look at its notes.

Don't modify anything.
