---
id: S-006
slug: loading-skeletons
title: Loading skeletons for planner and client list
status: dropped
model: sonnet
parallel: safe
depends_on: []
targets: [src/components/PlannerSkeleton.tsx, src/app/planner/loading.tsx, src/app/clients/loading.tsx]
patterns: [src/components/Card.tsx]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 1
dod:
  - pnpm exec tsc --noEmit
  - pnpm run lint
planned_at_sha: 8b21d0a
opportunity: loading-skeletons
notes: Superseded by streaming in S-008 (audit 2026-11-07)
---
## Goal
No layout jump while data loads.

## Context
Planner renders empty grid then pops in 800ms later.

## Steps
1. Skeleton component.
2. `loading.tsx` for both routes.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: Throttle network → skeletons render.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
None.

## Ready-to-run prompt
> Implement Apex session S-006 exactly as specified in `.apex/sessions/S-006-loading-skeletons.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-006`
