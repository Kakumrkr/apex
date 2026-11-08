---
id: S-004
slug: dashboard-error-boundaries
title: Error boundaries + retry on the dashboard and planner
status: done
model: sonnet
parallel: safe
depends_on: []
targets: [src/app/dashboard/error.tsx, src/app/planner/error.tsx, src/components/RetryButton.tsx]
patterns: [src/app/settings/error.tsx]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 1.5
dod:
  - pnpm exec tsc --noEmit
  - pnpm run test -- error
planned_at_sha: 8b21d0a
opportunity: error-boundaries
completed_at: "2026-10-15T18:30:00"
---
## Goal
A failed fetch shows a friendly retry instead of a white screen.

## Context
`src/app/dashboard/page.tsx:12` throws on 500s; no `error.tsx` anywhere except settings.

## Steps
1. Add `error.tsx` for dashboard + planner.
2. Extract a shared RetryButton.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: Kill the API → dashboard shows retry; restore → retry works.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
Low.

## Ready-to-run prompt
> Implement Apex session S-004 exactly as specified in `.apex/sessions/S-004-dashboard-error-boundaries.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-004`
