---
id: S-009
slug: ci-health-workflow
title: GitHub Actions CI running typecheck, lint, and tests
status: todo
model: sonnet
parallel: safe
depends_on: []
targets: [.github/workflows/ci.yml]
patterns: [package.json]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: 0.75
dod:
  - pnpm exec tsc --noEmit
  - pnpm run lint
planned_at_sha: c47e9f2
opportunity: ci-pipeline
---
## Goal
Every PR proves the build is green.

## Context
Health checks only run locally today; two regressions in October reached main.

## Steps
1. Workflow with pnpm cache running the four health checks.

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: Open a PR → CI runs and reports.
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
None.

## Ready-to-run prompt
> Implement Apex session S-009 exactly as specified in `.apex/sessions/S-009-ci-health-workflow.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session S-009`
