---
id: S-003
slug: planner-core-tests
title: Add tests for the weekly planner's capacity math
status: done
model: sonnet
parallel: safe
depends_on: []
targets: [src/lib/planner.test.ts]
patterns: [src/lib/format.test.ts]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 1
dod:
  - pnpm exec tsc --noEmit
  - pnpm run test -- planner
planned_at_sha: 3f9c2e1
opportunity: planner-tests
completed_at: "2026-09-22T21:12:00"
---
## Goal
Lock in overbooking detection before refactors.

## Context
The core value prop (overbooking warning) has zero tests.

## Steps
1. Table-test `computeCapacity()` edge cases.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: Tests pass; mutate the threshold and see them fail.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
None.

## Ready-to-run prompt
> Implement Apex session S-003 exactly as specified in `.apex/sessions/S-003-planner-core-tests.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-003`
