---
name: defer
description: Record an idea as Won't Fix or Deferred in Apex's permanent decisions log, so future audits never suggest it again (or only after a revisit date) and never dock the score for it.
argument-hint: "<slug | session-id | idea> [reason]"
disable-model-invocation: true
allowed-tools: Bash(python3 *), Read
---

# /apex:defer — log a Won't Fix / Deferred decision

APEX = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apex.py"` (always type the full
command). Arguments: `$ARGUMENTS`

1. **Resolve the target.**
   - If the argument is a session ID (`S-004`), read its packet with
     `APEX session show S-004` and use its `opportunity` slug and title.
   - If it matches a slug in `.apex/roadmap.md`'s Opportunities table, use that.
   - Otherwise treat it as a free-text idea and derive a kebab-case slug.
2. **Ask** with AskUserQuestion, unless the arguments already made it clear:
   - type: **Won't fix** (never suggest again) or **Deferred** (revisit later)
   - for Deferred: a revisit date (offer +1 month, +3 months, or no date)
   - a one-line reason, if none was given (future audits read it)
3. **Record it:**
   `APEX decision add --type wont-fix|deferred --slug <slug> --title "<title>" --reason "<reason>" [--revisit YYYY-MM-DD]`
4. **If a `todo` session packet implements this slug,** run
   `APEX session set-status <id> dropped --notes "<WF/DF id>"`.
5. Confirm in one line with the new decision ID. `.apex/decisions.md` is
   append-only: Claude's Write/Edit tools are blocked on it by design, so all
   changes go through this skill or the CLI.
