---
id: S-001
slug: validate-task-inputs
title: Validate task + client inputs with zod at the API boundary
status: done
model: sonnet
parallel: safe
depends_on: []
targets: [src/app/api/tasks/route.ts, src/app/api/clients/route.ts, src/lib/validation.ts]
patterns: [src/app/clients/page.tsx]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 1.5
dod:
  - pnpm exec tsc --noEmit
  - pnpm run test -- validation
planned_at_sha: 3f9c2e1
opportunity: api-input-validation
completed_at: "2026-09-16T19:40:00"
---
## Goal
Reject malformed task/client payloads instead of writing nulls to the DB.

## Context
`src/app/api/tasks/route.ts:18` spreads `req.json()` straight into `prisma.task.create`.

## Steps
1. Add zod schemas in `src/lib/validation.ts`.
2. Parse in both route handlers; return 422 with field errors.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: POST a task with no title → 422 with `title` error.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
Low. Revert the three files.

## Ready-to-run prompt
> Implement Apex session S-001 exactly as specified in `.apex/sessions/S-001-validate-task-inputs.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-001`
