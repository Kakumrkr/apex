# Demo: Tasklane (fictional)

A complete `.apex/` workspace for a **fictional** product, so you can try the Apex
CLI without installing anything or spending a single token. Competitors and URLs are
made up (`*.example.com`). The state, history snapshots, trend chart, and session
graph were produced by the real `apex.py` CLI across three simulated audits:

| Audit | Score | Tier | What happened |
|-------|------:|------|---------------|
| 2026-09-14 | 3.8 | 1 · Foundations | First full audit: unvalidated inputs, no strict types, no planner tests |
| 2026-10-12 | 5.1 | 2 · Reliability | S-001–S-003 shipped; promoted past the +0.3 hysteresis band |
| 2026-11-07 | 6.8 | 2 · Reliability | +1.7 jump, so the linter required a written `delta_justification` |

```bash
python3 ../../scripts/apex.py status --project-dir .
python3 ../../scripts/apex.py lint --project-dir .
python3 ../../scripts/apex.py session next --project-dir .
```

Start with `.apex/roadmap.md`, then open a packet such as
`.apex/sessions/S-008-optimistic-task-moves.md`.
