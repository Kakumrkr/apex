---
id: S-005
slug: starter-week-template
title: Seed a starter week so new users see value instantly
status: done
model: sonnet
parallel: safe
depends_on: []
targets: [src/app/onboarding/page.tsx, src/lib/templates.ts]
patterns: [src/app/clients/new/page.tsx]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 1.5
dod:
  - pnpm exec tsc --noEmit
  - pnpm run test -- templates
planned_at_sha: 8b21d0a
opportunity: starter-template
completed_at: "2026-10-20T09:45:00"
---
## Goal
Cut first-plan steps from 6 to 2.

## Context
Acme users complain weekly planning takes 'forever' to set up (forum thread in research).

## Steps
1. Template with 2 sample clients + 5 tasks.
2. 'Start with sample week' button on onboarding.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: New account → 'Start with sample week' → planner shows a populated week.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
Low; template is opt-in.

## Ready-to-run prompt
> Implement Apex session S-005 exactly as specified in `.apex/sessions/S-005-starter-week-template.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-005`
