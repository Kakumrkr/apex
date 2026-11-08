---
id: S-010
slug: planner-query-batching
title: Batch planner queries to remove the N+1 on week load
status: todo
model: sonnet
parallel: depends
depends_on: [S-008]
targets: [src/lib/planner-data.ts, src/app/planner/page.tsx]
patterns: [src/lib/client-data.ts]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 1.5
dod:
  - pnpm exec tsc --noEmit
  - pnpm run test -- planner-data
planned_at_sha: c47e9f2
opportunity: planner-n-plus-one
---
## Goal
Week view loads in one query instead of one per client.

## Context
`src/lib/planner-data.ts:27` loops clients and queries tasks per client (8 clients → 9 queries).

## Steps
1. Single `findMany` with `in` + group in memory.
2. Keep the public function signature.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: Load a week with 8 clients; Prisma log shows 2 queries.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
Low; covered by planner tests.

## Ready-to-run prompt
> Implement Apex session S-010 exactly as specified in `.apex/sessions/S-010-planner-query-batching.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-010`
