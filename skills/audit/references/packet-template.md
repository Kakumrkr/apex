# Session Packet Template (follow exactly)

Path: `.apex/sessions/S-###-<slug>.md`. The filename must equal `<id>-<slug>.md`.
A packet must be self-contained: a fresh session with no other context should be
able to execute it in 1-2 hours.

```markdown
---
id: S-004
slug: add-dashboard-error-boundaries
title: Add error boundaries and retry to the dashboard
status: todo                # todo | in_progress | done | blocked | dropped
model: sonnet               # sonnet = Standard Execution · opus = Deep Architecture
parallel: safe              # safe = no shared targets with any active packet · depends
depends_on: []              # e.g. [S-002]
targets: [src/app/dashboard/error.tsx, src/app/dashboard/page.tsx]   # 1-5 files
patterns: [src/app/settings/error.tsx]   # existing files to mirror for style
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 1.5         # 0.25-2.5
dod:
  - pnpm exec tsc --noEmit
  - pnpm run test -- dashboard
planned_at_sha: a1b2c3d
opportunity: error-boundaries   # slug from the roadmap's Opportunities table
---

## Goal
One or two sentences: the user-visible outcome.

## Context
Why now (the audit finding plus evidence `path:line`), relevant architecture, and
the gotchas found during the audit.

## Steps
1. Concrete, ordered steps referencing the target files.
2. …

## Definition of Done
- [ ] Every `dod` command passes.
- [ ] Manual flow: <exact clicks/requests to verify>.
- [ ] No files outside `targets` changed, except tests and `.apex/`.

## Risk & Rollback
Risk level (low/med/high), what could break, and how to revert.

## Ready-to-run prompt
> Implement Apex session S-004 exactly as specified in
> `.apex/sessions/S-004-add-dashboard-error-boundaries.md`. Mirror the style of the
> pattern files, stay within the target files, and run the DoD commands.
> Or simply: `/apex:run-session S-004`
```

## Rules
- `model: opus` only for cross-cutting architecture, data migrations, or tricky
  concurrency; everything else is `sonnet`.
- `parallel: safe` requires no target overlap with any other `todo`/`in_progress`
  packet **and** all `depends_on` done. Otherwise use `depends`.
- `dod` commands must be non-interactive and finish in under 10 minutes.
- Never include secrets. Use placeholders like `<API_KEY>`.
