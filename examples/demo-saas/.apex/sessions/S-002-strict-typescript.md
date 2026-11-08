---
id: S-002
slug: strict-typescript
title: Turn on strict mode and fix the core-loop types
status: done
model: opus
parallel: safe
depends_on: []
targets: [tsconfig.json, src/lib/planner.ts, src/types/task.ts]
patterns: [src/types/client.ts]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 2
dod:
  - pnpm exec tsc --noEmit
  - pnpm run lint
planned_at_sha: 3f9c2e1
opportunity: strict-types
completed_at: "2026-09-21T10:05:00"
---
## Goal
Catch null/undefined bugs in the planner at compile time.

## Context
`tsconfig.json:7` has `strict: false`; 41 implicit anys in `planner.ts`.

## Steps
1. Enable `strict`.
2. Fix errors in planner + task types only; `// @ts-expect-error` with TODO elsewhere.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: `pnpm exec tsc --noEmit` exits 0.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
Medium: type churn. Revert tsconfig to roll back.

## Ready-to-run prompt
> Implement Apex session S-002 exactly as specified in `.apex/sessions/S-002-strict-typescript.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-002`
