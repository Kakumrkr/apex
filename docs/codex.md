# Using Apex with OpenAI Codex (prompt-only mode)

Codex supports `SKILL.md` skills (in `.agents/skills/` per repo or
`~/.agents/skills/` globally) but not Claude Code plugins, subagents, or hooks.
Apex still works there with the same workflow, files, and CLI, but **nothing
enforces the guardrails**.

```bash
git clone https://github.com/Kakumrkr/apex.git ~/apex
cd your-project
~/apex/scripts/install-codex.sh            # project-level: ./.agents
# or: ~/apex/scripts/install-codex.sh ~/.agents   (global)
```

Then in Codex: `$apex-init`, `$apex-audit`, `$apex-run-session S-001`, `$apex-status`, `$apex-defer`.

| Feature | Claude Code | Codex |
|---|---|---|
| North Star, decisions, roadmap, packets, history | ✅ | ✅ |
| `apex.py` lint, finalize, health, status | ✅ | ✅ (run by the skill) |
| Isolated auditor subagent | ✅ | ❌ (runs inline) |
| Write/Bash/Read guards | ✅ enforced | ❌ instructions only |
| URL provenance log | ✅ automatic | ❌ can't verify, so mark everything `unverified` |
| Lint gate before the audit can finish | ✅ hook | ⚠️ the skill asks the agent to run lint |

Because provenance can't be logged in Codex, `verified` parity rows fail lint
unless the URL is in committed research. That's intentional.
