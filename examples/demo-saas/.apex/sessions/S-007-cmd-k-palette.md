---
id: S-007
slug: cmd-k-palette
title: Cmd+K command palette for clients, tasks, and weeks
status: in_progress
model: sonnet
parallel: safe
depends_on: []
targets: [src/components/CommandPalette.tsx, src/hooks/useHotkeys.ts, src/app/layout.tsx]
patterns: [src/components/ClientPicker.tsx]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 1.5
dod:
  - pnpm exec tsc --noEmit
  - pnpm run test -- CommandPalette
planned_at_sha: c47e9f2
opportunity: cmd-k-palette
started_at: "2026-11-08T08:55:00"
---
## Goal
Jump to any client, task, or week in two keystrokes.

## Context
Boardly reviewers repeatedly ask for keyboard navigation (reviews.example.com). Our power users plan on Mondays with both hands on the keyboard.

## Steps
1. `useHotkeys` hook (mirror `ClientPicker` focus handling).
2. Palette with fuzzy search over clients/tasks/weeks.
3. Mount in root layout.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: Press ⌘K → type 'acme' → Enter opens that client.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
Low; palette is additive. Revert the three files.

## Ready-to-run prompt
> Implement Apex session S-007 exactly as specified in `.apex/sessions/S-007-cmd-k-palette.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-007`
