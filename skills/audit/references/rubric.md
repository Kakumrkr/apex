# Apex Scoring Rubric (v1)

Score each dimension **1.0-10.0** (one decimal). `overall` is the weighted mean;
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

**How to use this file:** read "Hard rules" and "Anchors" every audit. Then read
only the stack checklists that match `config.json` `stack` (for example
`JS/TS · Next.js` + `JS/TS · Node API`). Each checklist item is a probe: a
command or file to inspect, the dimension it feeds, and what "bad" looks like.
All commands below pass the auditor's read-only Bash guard; prefer the Grep/Glob
tools when you don't need a pipeline.

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
- **One finding, one dimension.** Don't punish the same missing error boundary
  under both `resilience` and `ux_onboarding`; pick the dimension the user feels.

## Anchors (what a score means)
| Score | Meaning |
|------:|---------|
| 1-2 | Doesn't run, or the core loop is missing. |
| 3-4 | Core loop works on the happy path only; frequent crashes or data loss risk. |
| 5-6 | Usable by a forgiving early adopter; obvious rough edges. |
| 7-8 | Reliable and pleasant; a paying user would stay. |
| 9 | Best-in-class on this dimension vs. the North Star competitors. |
| 10 | Category-defining; competitors copy you. Rare, and needs external evidence. |

### Per-dimension anchors
| Dimension | 3 looks like | 6 looks like | 8 looks like |
|-----------|--------------|--------------|--------------|
| core_loop | Happy path only; a stubbed handler or dead route on the critical path | Works end to end; 1-2 rough steps or a manual workaround | Fast, complete, no dead ends; edge inputs handled |
| data_integrity | No validation at the boundary; writes without transactions | Schema-validated inputs; migrations exist; some multi-step writes unguarded | Validation + constraints + transactions + idempotent retries |
| ux_onboarding | Blank screens while loading; raw errors; no empty states | Loading and error states on main views; first run needs docs | Skeletons, helpful empty states, first value in <60s, accessible |
| code_health | `strict` off, widespread `any` / untyped Python, lint failing | Strict on with pockets of `any`; some duplication | Strict, typed boundaries, lint clean, clear module ownership |
| resilience | Uncaught promise rejections; one failed fetch breaks the page | Error boundaries on main routes; some timeouts | Timeouts, retries with backoff, degraded modes, structured logs |
| performance | N+1 queries on the main list; unbounded fetches | Paginated main lists; obvious hot spots remain | Measured budgets, caching, no N+1, lean bundles |
| testing | No tests, or tests that assert nothing | Unit tests on the core loop; CI runs some checks | Core loop covered incl. failure paths; CI gates merges |
| security | AuthZ missing on mutations, or secrets in the repo | AuthN everywhere, authZ mostly; validation present | AuthZ on every mutation, rate limits on auth, clean advisories |

## Universal probes (every stack)
- **Critical-path TODOs** (core_loop): `rg -n 'TODO|FIXME|HACK|XXX' src app lib`. Bad: TODO inside the core loop's handler.
- **Stubbed handlers** (core_loop): `rg -n 'not implemented|NotImplementedError|throw new Error.(TODO|Not implemented)' src app`. Bad: Reachable from a route.
- **Dead feature flags** (core_loop): `rg -n 'FEATURE_|featureFlag|flags\.' src app`. Bad: Core value behind a flag that's off by default.
- **Churn hot spots** (code_health): `git log --since=90.days --name-only --format= | sort | uniq -c | sort -rn | head -15`. Bad: One file changed in most commits = fragile core.
- **Size outliers** (code_health): `git ls-files | rg '\.(ts|tsx|py)$' | head -400` then `wc -l` on the biggest. Bad: Files >600 lines mixing UI, data, and logic.
- **Committed secrets** (security): `git ls-files | rg -i '(^|/)\.env($|\.)|\.pem$|id_rsa'`. Bad: Any hit that isn't `.env.example`.
- **CI exists** (testing): `ls .github/workflows` and Read the YAML. Bad: No CI, or CI that skips tests.
- **Skipped tests** (testing): `rg -n '\.skip\(|xit\(|xdescribe\(|@pytest\.mark\.skip|@unittest\.skip' .`. Bad: Skips on the core loop.

## JS/TS checklists

### JS/TS · React (any framework)
- **Loading states** (ux_onboarding): `rg -n 'isLoading|isPending|<Suspense|Skeleton' src --glob '*.tsx'`. Bad: Data views with no loading branch.
- **Empty states** (ux_onboarding): `rg -n 'length === 0|\.length \?|EmptyState|No .* yet' src --glob '*.tsx'`. Bad: Lists that render nothing when empty.
- **Error boundaries** (resilience): `rg -n 'ErrorBoundary|componentDidCatch|error\.tsx' src app`. Bad: None around data-heavy routes.
- **Effect fetching** (resilience): `rg -n 'useEffect\(' src --glob '*.tsx'` then Read the hits. Bad: `fetch` in `useEffect` without abort/cleanup or error state.
- **Keys** (ux_onboarding): `rg -n 'key=\{(i|index|idx)\}' src --glob '*.tsx'`. Bad: Index keys on reorderable lists.
- **`any` density** (code_health): `rg -c ': any\b|as any\b|<any>' src`. Bad: >1 per 200 lines; any on API boundaries.
- **Ts-ignores** (code_health): `rg -n '@ts-ignore|@ts-expect-error|eslint-disable' src`. Bad: Clustered in core modules.
- **Accessibility** (ux_onboarding): `rg -n '<img ' src --glob '*.tsx' | rg -v 'alt='`, `rg -n '<div[^>]*onClick' src --glob '*.tsx'`, and `rg -n 'aria-|role=' src`. Bad: Clickable divs, images without alt, no labels on inputs.
- **Forms** (ux_onboarding): `rg -n 'useForm|zodResolver|onSubmit' src --glob '*.tsx'`. Bad: Submit without disabled/pending state; no inline errors.
- **XSS sinks** (security): `rg -n 'dangerouslySetInnerHTML|innerHTML\s*=' src`. Bad: Unsanitized user content.
- **Bundle weight** (performance): Read `package.json` deps. Bad: moment, lodash (full), multiple chart/icon libs on the client.
- **List rendering** (performance): `rg -n '\.map\(' src --glob '*.tsx'` near data hooks. Bad: Unbounded lists with no pagination or virtualization.

### JS/TS · Next.js
- **Router style** (code_health): `ls app pages src/app src/pages 2>/dev/null`. Bad: Mixed routers without a reason.
- **Route states** (ux_onboarding / resilience): `find app src/app -name 'loading.tsx' -o -name 'error.tsx' -o -name 'not-found.tsx'`. Bad: Data routes missing `loading.tsx` / `error.tsx`.
- **Client sprawl** (performance): `rg -l "^'use client'|^\"use client\"" app src` count vs. total. Bad: Whole pages marked client to use one hook.
- **Server Actions authZ** (security): `rg -n "'use server'" app src` then Read each action. Bad: Action mutates data without checking the session.
- **Route handlers** (security / data_integrity): `find app src/app -name 'route.ts'` then Read. Bad: No input validation (zod) or authZ in POST/PATCH/DELETE.
- **Env leakage** (security): `rg -n 'NEXT_PUBLIC_' src app`. Bad: Secrets behind `NEXT_PUBLIC_`.
- **Caching** (performance): `rg -n 'revalidate|cache:|unstable_cache|dynamic =' app src`. Bad: Every page `force-dynamic`; or stale data on user-specific pages.
- **Images** (performance): `rg -n '<img ' app src --glob '*.tsx'`. Bad: Raw `<img>` for large assets instead of `next/image`.
- **Middleware** (security): Read `middleware.ts`. Bad: Auth gate only in middleware, not re-checked in actions/handlers.

### JS/TS · Node API (Express / Fastify / Hono / tRPC / NestJS)
- **Validation** (data_integrity): `rg -n 'z\.object|Joi\.|yup\.|class-validator|schema:' src`. Bad: Handlers reading `req.body` with no schema.
- **AuthZ on mutations** (security): `rg -n '\.(post|put|patch|delete)\(' src` then Read. Bad: Ownership not checked (`where: { id }` without `userId`).
- **Async errors** (resilience): `rg -n 'async \(req, res' src`. Bad: No error middleware / unhandled rejections in Express 4.
- **Timeouts** (resilience): `rg -n 'timeout|AbortSignal\.timeout|signal:' src`. Bad: Outbound fetch/HTTP with no timeout.
- **Rate limits** (security): `rg -n 'rateLimit|rate-limit|@fastify/rate-limit|throttle' src`. Bad: None on login/signup/reset.
- **N+1** (performance): `rg -n 'for .* of .*\) \{' src -A4 | rg 'await .*find'`. Bad: `await` a query inside a loop.
- **Transactions** (data_integrity): `rg -n '\$transaction|transaction\(|BEGIN' src`. Bad: Multi-write flows (order + items) without one.
- **ORM schema** (data_integrity): Read `prisma/schema.prisma` or `drizzle/*.ts`. Bad: Missing `@unique` / FK / indexes on lookup columns.
- **Logging** (resilience / security): `rg -n 'console\.log' src | wc -l` vs. a logger. Bad: Only console.log; logs include tokens or PII.
- **Advisories** (security): `npm audit --omit=dev --json` (only if lockfile exists). Bad: High/critical in runtime deps.

## Python checklists

### Python · FastAPI
- **Models at the boundary** (data_integrity): `rg -n '@(app|router)\.(post|put|patch)' -A3 app src`. Bad: `dict` / `Request` bodies instead of Pydantic models.
- **Response models** (security): `rg -n 'response_model=' app src`. Bad: Endpoints returning ORM objects (leaks fields).
- **AuthZ dependency** (security): `rg -n 'Depends\(' app src`. Bad: Mutations without a current-user dependency, or no ownership check.
- **Blocking in async** (performance): `rg -n 'async def' -A15 app src | rg 'requests\.|time\.sleep|open\('`. Bad: Sync I/O inside `async def`.
- **Sessions/transactions** (data_integrity): `rg -n 'SessionLocal|get_db|commit\(\)|rollback\(\)' app src`. Bad: Commit per statement; no rollback on error.
- **Error handling** (resilience): `rg -n 'HTTPException|exception_handler' app src`. Bad: Bare `except:` / 500s with stack traces to clients.
- **Migrations** (data_integrity): `ls alembic/versions migrations 2>/dev/null`. Bad: Models change without migrations.
- **CORS** (security): `rg -n 'CORSMiddleware' -A5 app src`. Bad: `allow_origins=['*']` with credentials.
- **Tests** (testing): `rg -n 'TestClient|AsyncClient|httpx' tests`. Bad: No API-level tests on the core endpoints.

### Python · Django
- **Settings hygiene** (security): Read `settings.py` / `settings/*.py`. Bad: `DEBUG = True` default, hard-coded `SECRET_KEY`, `ALLOWED_HOSTS = ['*']`.
- **N+1** (performance): `rg -n 'objects\.(all|filter)\(' -A3 . --glob '*.py' | rg 'for '` and templates looping relations. Bad: No `select_related` / `prefetch_related` on list views.
- **AuthZ** (security): `rg -n 'login_required|LoginRequiredMixin|permission_required|has_perm' .`. Bad: Views returning other users' objects (`get(pk=...)` without owner filter).
- **Forms/validation** (data_integrity): `rg -n 'forms\.ModelForm|serializers\.' .`. Bad: `request.POST[...]` used directly.
- **Migrations** (data_integrity): `ls */migrations`. Bad: Missing migrations; `RunPython` without reverse.
- **Transactions** (data_integrity): `rg -n 'transaction\.atomic' .`. Bad: Multi-model writes outside `atomic`.
- **Raw SQL** (security): `rg -n '\.raw\(|cursor\.execute\(|extra\(' .`. Bad: f-strings into SQL.
- **Templates** (security): `rg -n '\|safe|mark_safe' . --glob '*.html' --glob '*.py'`. Bad: User content marked safe.
- **Admin exposure** (security): `rg -n 'admin\.site\.urls' .`. Bad: Default `/admin/` with no extra protection on a public app.
- **Tests** (testing): `rg -n 'TestCase|pytest\.mark\.django_db' .`. Bad: No view or model tests on the core flow.

### Python · CLI tools (click / typer / argparse)
- **Entry point** (ux_onboarding): Read `pyproject.toml` `[project.scripts]`. Bad: No console script; README says `python main.py`.
- **Help text** (ux_onboarding): `rg -n 'help=|add_argument\(' src`. Bad: Options without help; no examples in `--help`.
- **Exit codes** (resilience): `rg -n 'sys\.exit\(|raise SystemExit|typer\.Exit|ctx\.exit' src`. Bad: Errors exit 0; tracebacks shown for user mistakes.
- **Errors** (resilience): `rg -n 'except Exception|except:' src`. Bad: Swallowed errors; no actionable message.
- **Destructive ops** (data_integrity): `rg -n 'shutil\.rmtree|os\.remove|unlink\(' src`. Bad: No `--dry-run` / confirmation on destructive commands.
- **Config** (security): `rg -n 'environ|getenv|configparser|tomllib' src`. Bad: Secrets read from flags (land in shell history).
- **Subprocess** (security): `rg -n 'shell=True|os\.system' src`. Bad: Shell strings built from user input.
- **Startup time** (performance): Read the entry module's top-level imports. Bad: Heavy imports (pandas, torch) at module top for every command.
- **Output** (ux_onboarding): `rg -n 'print\(' src | wc -l` vs. `rich`/`logging`. Bad: No `--json`/quiet mode for scripting.
- **Tests** (testing): `rg -n 'CliRunner|capsys|subprocess\.run' tests`. Bad: Commands untested end to end.

### Python · general
- Typing: `rg -c '# type: ignore|: Any\b|-> Any\b' src`; is `mypy`/`pyright` in CI and strict on the core package? (code_health)
- Packaging: one of `pyproject.toml` / `requirements*.txt` with pinned versions; a lockfile for apps. (resilience)
- Advisories: `pip-audit` only if already installed (`python -m pip_audit`). (security)

## Writing the evidence
- Cite the most specific line: `src/api/tasks.ts:42 - POST /tasks has no ownership check`.
- One evidence line per dimension in the Scorecard table; extra findings go in Opportunities.
- When a health check is the evidence, name it: `health:typecheck fail (12 errors)`.
