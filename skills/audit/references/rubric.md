# Apex Scoring Rubric (v1)

Score each dimension **1.0–10.0** (one decimal). `overall` is the weighted mean;
`apex.py lint` recomputes it and rejects anything off by more than ±0.15.

| Key | Dimension | Weight |
|-----|-----------|-------:|
| `core_loop` | Core loop & functionality | 20 |
| `data_integrity` | Data & schema integrity | 15 |
| `ux_onboarding` | UX states & onboarding | 15 |
| `code_health` | Type safety & code health | 10 |
| `resilience` | Error handling & resilience | 10 |
| `performance` | Performance | 10 |
| `testing` | Tests & CI | 10 |
| `security` | Security & privacy | 10 |

## Hard rules
- **Broken build cap:** if any *required* health check fails, `overall ≤ 4.5`.
- **Evidence:** each dimension cites at least one `path:line` (or a health-check
  result) in the Scorecard table. No evidence means you can't score above 5.0.
- **Confidence:** `high` = read the relevant code paths; `medium` = sampled;
  `low` = inferred from structure. Use `low` honestly in delta mode for modules
  you didn't re-read.
- **Non-goals and won't-fix items never reduce the score.**
- **Score the product that exists, not the plan.** TODOs, commented-out code, and
  open branches count for nothing.
- **Big moves (>1.5 vs. last audit)** need a `delta_justification` citing evidence.

## Anchors (what a score means)
| Score | Meaning |
|------:|---------|
| 1–2 | Doesn't run, or the core loop is missing. |
| 3–4 | Core loop works on the happy path only; frequent crashes/data loss risk. |
| 5–6 | Usable by a forgiving early adopter; obvious rough edges. |
| 7–8 | Reliable and pleasant; a paying user would stay. |
| 9 | Best-in-class on this dimension vs. the North Star competitors. |
| 10 | Category-defining; competitors copy you. Rare — needs external evidence. |

## What to look at per dimension
- **core_loop:** Can the target user reach the core value end to end? Dead routes,
  stubbed handlers, `TODO` in the critical path, and feature flags left off.
- **data_integrity:** Schema/migrations, validation at boundaries (zod/pydantic),
  transactions, idempotency, unique constraints, orphaned records, and backups.
- **ux_onboarding:** Loading, empty, and error states; skeletons; first-run
  experience; copy clarity; accessibility basics (labels, focus, contrast).
- **code_health:** `strict` TS / typed Python, `any`/`# type: ignore` density,
  dead code, duplication, module boundaries, and lint status.
- **resilience:** Error boundaries, retries with backoff, timeouts, graceful
  degradation, user-facing error messages, and logging.
- **performance:** N+1 queries, bundle size, unbounded lists, missing pagination,
  caching, image handling, and blocking work on hot paths.
- **testing:** Tests on the core loop, CI config, flaky/skipped tests, and the health
  check results.
- **security:** AuthZ on every mutation, input validation, secrets in the repo,
  dependency advisories (`npm audit` / `pip-audit` only if already installed),
  CSRF/XSS/SQLi patterns, and rate limiting on auth.
