---
id: S-008
slug: optimistic-task-moves
title: Optimistic drag-to-reschedule with instant undo
status: todo
model: opus
parallel: safe
depends_on: []
targets: [src/app/planner/actions.ts, src/components/WeekGrid.tsx, src/components/UndoToast.tsx]
patterns: [src/app/clients/actions.ts]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 2
dod:
  - pnpm exec tsc --noEmit
  - pnpm run test -- WeekGrid
planned_at_sha: c47e9f2
opportunity: optimistic-reschedule
---
## Goal
Rescheduling feels instant and is always reversible.

## Context
Each drag waits ~400ms for the server (`src/app/planner/actions.ts:44`). Acme's top complaint is 'laggy drag and drop'.

## Steps
1. `useOptimistic` in WeekGrid.
2. Server action returns canonical state; reconcile.
3. UndoToast with 5s window.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: Drag a task to Thursday → moves instantly → Undo restores it; offline → toast explains and reverts.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
Medium: race conditions on rapid drags. Feature-flag `optimisticMoves`.

## Ready-to-run prompt
> Implement Apex session S-008 exactly as specified in `.apex/sessions/S-008-optimistic-task-moves.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-008`
