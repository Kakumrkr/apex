"""Regenerate examples/demo-saas by driving the real Apex CLI/API through 3 audits.

Usage: python3 examples/generate_demo.py   (from anywhere; rewrites examples/demo-saas)
"""
import datetime, json, os, shutil, subprocess, sys, textwrap

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "examples", "demo-saas")
# Build in a throwaway git repo: lint compares done packets against HEAD, and the
# committed demo's packets are already done there.
import tempfile
WORK = tempfile.mkdtemp(prefix="apex-demo-")
DEMO = os.path.join(WORK, "demo-saas")
_env = dict(os.environ, GIT_AUTHOR_NAME="demo", GIT_AUTHOR_EMAIL="demo@example.com",
            GIT_COMMITTER_NAME="demo", GIT_COMMITTER_EMAIL="demo@example.com")
subprocess.run(["git", "init", "-q", WORK], check=True)
subprocess.run(["git", "-C", WORK, "commit", "-q", "--allow-empty", "-m", "demo"], check=True, env=_env)
sys.path.insert(0, os.path.join(REPO, "scripts"))
from apex_core.paths import ApexPaths
from apex_core import decisions, sessions, audit

shutil.rmtree(DEMO, ignore_errors=True)
os.makedirs(DEMO)
p = ApexPaths(DEMO)
APEX = [sys.executable, os.path.join(REPO, "scripts", "apex.py")]

def cli(*args, stdin=None):
    r = subprocess.run(APEX + list(args) + ["--project-dir", DEMO], input=stdin, capture_output=True, text=True)
    if r.returncode not in (0,):
        raise SystemExit(f"apex {args} failed: {r.stdout}\n{r.stderr}")
    return r.stdout

def w(rel, text):
    path = os.path.join(DEMO, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(textwrap.dedent(text).lstrip("\n"))

# ---------- init -----------------------------------------------------------
spec = {
    "product": "Tasklane (fictional demo)",
    "audience": "Freelancers and solo consultants juggling 3-8 clients who plan their week on Monday morning",
    "value": "Plan a realistic week across every client in under 60 seconds, and see when you're overbooked before you say yes",
    "competitors": ["Acme Tasks (fictional)", "Boardly (fictional)"],
    "non_goals": ["Team/enterprise features (SSO, RBAC, admin consoles)", "Invoicing or time-tracking for billing", "Native mobile apps before web PMF"],
    "stack": ["javascript", "typescript", "next", "react"], "package_manager": "pnpm",
    "research": True,
    "health_checks": [
        {"name": "typecheck", "cmd": "pnpm exec tsc --noEmit", "required": True, "timeout": 300},
        {"name": "lint", "cmd": "pnpm run lint", "required": False, "timeout": 300},
        {"name": "test", "cmd": "pnpm run test", "required": False, "timeout": 600},
        {"name": "build", "cmd": "pnpm run build", "required": True, "timeout": 600},
    ],
}
cli("init", stdin=json.dumps(spec))
# init stamps today's date on the North Star; the story starts at the first audit.
ns = open(p.north_star).read().replace(f"on {datetime.date.today().isoformat()}", "on 2026-09-14")
open(p.north_star, "w").write(ns)
decisions.add(p, "wont-fix", "SSO / SAML login", "Explicit non-goal: solo freelancers, not teams", slug="sso-login", today="2026-09-14")
decisions.add(p, "deferred", "Calendar two-way sync", "Valuable but 4+ sessions; revisit after onboarding is fixed",
              slug="calendar-two-way-sync", revisit="2027-01-15", today="2026-10-12")

PACKET = """
---
id: {id}
slug: {slug}
title: {title}
status: todo
model: {model}
parallel: {parallel}
depends_on: [{deps}]
targets: [{targets}]
patterns: [{patterns}]
do_not_touch: [prisma/schema.prisma, src/lib/auth]
estimate_hours: {est}
dod:
  - pnpm exec tsc --noEmit
  - {dod}
planned_at_sha: {sha}
opportunity: {opp}
---
## Goal
{goal}

## Context
{context}

## Steps
{steps}

## Definition of Done
- [ ] All `dod` commands pass.
- [ ] Manual flow: {flow}
- [ ] No files outside `targets` changed (tests and `.apex/` excepted).

## Risk & Rollback
{risk}

## Ready-to-run prompt
> Implement Apex session {id} exactly as specified in `.apex/sessions/{id}-{slug}.md`.
> Mirror the pattern files, stay inside the targets, and run the DoD commands.
> Or simply: `/apex:run-session {id}`
"""

def packet(**kw):
    kw.setdefault("deps", ""); kw.setdefault("model", "sonnet"); kw.setdefault("parallel", "safe")
    kw.setdefault("est", 1.5); kw.setdefault("patterns", "src/app/clients/page.tsx")
    w(f".apex/sessions/{kw['id']}-{kw['slug']}.md", PACKET.format(**kw))

CARD = lambda **kw: json.dumps(kw)

def roadmap(card, body):
    w(".apex/roadmap.md", f"# Apex Roadmap: Tasklane (fictional demo)\n\n<!-- apex:scorecard {card} -->\n\n" + textwrap.dedent(body).lstrip("\n"))

w(".apex/.search-log.json", json.dumps({"urls": {
    "https://acmetasks.example.com/features": {"domain": "acmetasks.example.com", "tool": "WebFetch", "first_seen": "2026-10-12T10:02:11"},
    "https://acmetasks.example.com/pricing": {"domain": "acmetasks.example.com", "tool": "WebSearch", "first_seen": "2026-10-12T10:01:40"},
    "https://forum.example.com/t/acme-tasks-weekly-planning-is-painful/4411": {"domain": "forum.example.com", "tool": "WebSearch", "first_seen": "2026-10-12T10:03:05"},
    "https://boardly.example.com/templates": {"domain": "boardly.example.com", "tool": "WebFetch", "first_seen": "2026-11-07T09:12:51"},
    "https://reviews.example.com/boardly/cons": {"domain": "reviews.example.com", "tool": "WebSearch", "first_seen": "2026-11-07T09:14:20"},
}}, indent=1) + "\n")

# ---------- Audit 1 (Tier 1) --------------------------------------------
d1 = {"core_loop": 4.5, "data_integrity": 3.5, "ux_onboarding": 3.5, "code_health": 4.0,
      "resilience": 3.0, "performance": 5.0, "testing": 2.5, "security": 4.0}   # weighted 3.825
for kw in [
    dict(id="S-001", slug="validate-task-inputs", title="Validate task + client inputs with zod at the API boundary",
         targets="src/app/api/tasks/route.ts, src/app/api/clients/route.ts, src/lib/validation.ts", dod="pnpm run test -- validation",
         sha="3f9c2e1", opp="api-input-validation", goal="Reject malformed task/client payloads instead of writing nulls to the DB.",
         context="`src/app/api/tasks/route.ts:18` spreads `req.json()` straight into `prisma.task.create`.",
         steps="1. Add zod schemas in `src/lib/validation.ts`.\n2. Parse in both route handlers; return 422 with field errors.",
         flow="POST a task with no title → 422 with `title` error.", risk="Low. Revert the three files."),
    dict(id="S-002", slug="strict-typescript", title="Turn on strict mode and fix the core-loop types",
         targets="tsconfig.json, src/lib/planner.ts, src/types/task.ts", dod="pnpm run lint", model="opus", est=2,
         patterns="src/types/client.ts", sha="3f9c2e1", opp="strict-types",
         goal="Catch null/undefined bugs in the planner at compile time.", context="`tsconfig.json:7` has `strict: false`; 41 implicit anys in `planner.ts`.",
         steps="1. Enable `strict`.\n2. Fix errors in planner + task types only; `// @ts-expect-error` with TODO elsewhere.",
         flow="`pnpm exec tsc --noEmit` exits 0.", risk="Medium: type churn. Revert tsconfig to roll back."),
    dict(id="S-003", slug="planner-core-tests", title="Add tests for the weekly planner's capacity math",
         targets="src/lib/planner.test.ts", dod="pnpm run test -- planner", sha="3f9c2e1", opp="planner-tests",
         patterns="src/lib/format.test.ts", est=1, goal="Lock in overbooking detection before refactors.",
         context="The core value prop (overbooking warning) has zero tests.", steps="1. Table-test `computeCapacity()` edge cases.",
         flow="Tests pass; mutate the threshold and see them fail.", risk="None."),
]:
    packet(**kw)
roadmap(CARD(date="2026-09-14", mode="full", sha="3f9c2e1", overall=3.8, confidence="medium", research="light",
             health={"status": "partial"}, dimensions=d1), """
> **North Star:** freelancers plan a realistic multi-client week in <60s · see `north-star.md`
> **Score 3.8 / 10 · Tier 1 · Foundations.** The planner works on the happy path, but unvalidated inputs and missing types put data at risk.

## Scorecard
| Dimension | Weight | Score | Confidence | Evidence |
|---|---:|---:|---|---|
| Core loop | 20 | 4.5 | high | `src/lib/planner.ts:88` capacity math works; no overbooking UI yet |
| Data integrity | 15 | 3.5 | high | `src/app/api/tasks/route.ts:18` writes unvalidated JSON |
| UX & onboarding | 15 | 3.5 | medium | blank dashboard on first login |
| Code health | 10 | 4.0 | high | `tsconfig.json:7` strict off |
| Resilience | 10 | 3.0 | medium | no error boundaries |
| Performance | 10 | 5.0 | low | small data sets only |
| Tests & CI | 10 | 2.5 | high | 2 tests, none on the planner |
| Security | 10 | 4.0 | medium | authZ checked on reads only |

### Score trend
<!-- apex:trend:start -->
<!-- apex:trend:end -->

## Health Check
| Check | Result | Notes |
|---|---|---|
| typecheck | pass | non-strict |
| lint | fail | 23 warnings treated as errors |

## Progress Since Last Audit
First audit.

## First 60 Seconds
Sign-up → empty dashboard → "New client" → "New task". **6 steps** to first plan; no template.

## Parity Matrix
| Workflow | Competitor | Verdict | Evidence | Source | Verified | Checked |
|---|---|---|---|---|---|---|
| Weekly planning | Acme Tasks (fictional) | Missing | They have a week view; we have a list | - | unverified | 2026-09-14 |

## Opportunities
| Slug | Opportunity | Impact | Effort (sessions) | ROI | Tier | Checked |
|---|---|---:|---:|---:|---:|---|
| `api-input-validation` | zod validation at API boundary | 5 | 1 | 5.0 | 1 | - |
| `strict-types` | Strict TypeScript on the core loop | 4 | 1 | 4.0 | 1 | - |
| `planner-tests` | Planner capacity tests | 4 | 1 | 4.0 | 1 | - |

**Decisions honored:** WF-001

## Session Plan
<!-- apex:sessions:start -->
<!-- apex:sessions:end -->

## Questions for the owner
- Is a weekly calendar view in scope for v1?

## Next audit focus
- Verify S-001..S-003 landed; re-check lint.
""")
print(cli("finalize-audit", "--date", "2026-09-14"))
for sid, day in (("S-001", "2026-09-16T19:40:00"), ("S-002", "2026-09-21T10:05:00"), ("S-003", "2026-09-22T21:12:00")):
    sessions.set_status(p, sid, "done", today=day)

# ---------- Audit 2 (-> Tier 2) ------------------------------------------
d2 = {"core_loop": 5.5, "data_integrity": 5.5, "ux_onboarding": 4.5, "code_health": 5.5,
      "resilience": 4.0, "performance": 5.0, "testing": 4.5, "security": 5.0}  # 5.075
for kw in [
    dict(id="S-004", slug="dashboard-error-boundaries", title="Error boundaries + retry on the dashboard and planner",
         targets="src/app/dashboard/error.tsx, src/app/planner/error.tsx, src/components/RetryButton.tsx",
         patterns="src/app/settings/error.tsx", dod="pnpm run test -- error", sha="8b21d0a", opp="error-boundaries",
         goal="A failed fetch shows a friendly retry instead of a white screen.", context="`src/app/dashboard/page.tsx:12` throws on 500s; no `error.tsx` anywhere except settings.",
         steps="1. Add `error.tsx` for dashboard + planner.\n2. Extract a shared RetryButton.", flow="Kill the API → dashboard shows retry; restore → retry works.",
         risk="Low."),
    dict(id="S-005", slug="starter-week-template", title="Seed a starter week so new users see value instantly",
         targets="src/app/onboarding/page.tsx, src/lib/templates.ts", dod="pnpm run test -- templates", sha="8b21d0a",
         opp="starter-template", patterns="src/app/clients/new/page.tsx", goal="Cut first-plan steps from 6 to 2.",
         context="Acme users complain weekly planning takes 'forever' to set up (forum thread in research).",
         steps="1. Template with 2 sample clients + 5 tasks.\n2. 'Start with sample week' button on onboarding.",
         flow="New account → 'Start with sample week' → planner shows a populated week.", risk="Low; template is opt-in."),
    dict(id="S-006", slug="loading-skeletons", title="Loading skeletons for planner and client list",
         targets="src/components/PlannerSkeleton.tsx, src/app/planner/loading.tsx, src/app/clients/loading.tsx",
         patterns="src/components/Card.tsx", dod="pnpm run lint", sha="8b21d0a", opp="loading-skeletons", est=1,
         goal="No layout jump while data loads.", context="Planner renders empty grid then pops in 800ms later.",
         steps="1. Skeleton component.\n2. `loading.tsx` for both routes.", flow="Throttle network → skeletons render.", risk="None."),
]:
    packet(**kw)
roadmap(CARD(date="2026-10-12", mode="standard", sha="8b21d0a", overall=5.1, confidence="medium", research="full",
             health={"status": "pass"}, dimensions=d2), """
> **North Star:** freelancers plan a realistic multi-client week in <60s · see `north-star.md`
> **Score 5.1 / 10 · Tier 2 · Reliability.** Foundations are solid; first-run experience and error states now limit retention.

## Scorecard
| Dimension | Weight | Score | Confidence | Evidence |
|---|---:|---:|---|---|
| Core loop | 20 | 5.5 | high | overbooking warning shipped `src/lib/planner.ts:131` |
| Data integrity | 15 | 5.5 | high | zod at both API routes (S-001) |
| UX & onboarding | 15 | 4.5 | high | 6-step empty start |
| Code health | 10 | 5.5 | high | strict mode on (S-002) |
| Resilience | 10 | 4.0 | high | white screen on API 500 |
| Performance | 10 | 5.0 | low | unchanged |
| Tests & CI | 10 | 4.5 | high | planner tests (S-003); no CI yet |
| Security | 10 | 5.0 | medium | authZ on mutations |

### Score trend
<!-- apex:trend:start -->
<!-- apex:trend:end -->

## Health Check
| Check | Result | Notes |
|---|---|---|
| typecheck | pass | strict |
| lint | pass | |
| test | pass | 19 tests |
| build | pass | |

## Progress Since Last Audit
- **Sessions done:** S-001, S-002, S-003 (all planned work landed) · **Off-plan:** overbooking banner
- Tier 1 → Tier 2.

## First 60 Seconds
Still **6 steps** to a first plan; Acme Tasks needs 3.

## Parity Matrix
| Workflow | Competitor | Verdict | Evidence | Source | Verified | Checked |
|---|---|---|---|---|---|---|
| Weekly planning | Acme Tasks (fictional) | Matches | Both have a week view | https://acmetasks.example.com/features | verified | 2026-10-12 |
| Overbooking warning | Acme Tasks (fictional) | Beats | They have no capacity model | https://forum.example.com/t/acme-tasks-weekly-planning-is-painful/4411 | verified | 2026-10-12 |

## Opportunities
| Slug | Opportunity | Impact | Effort (sessions) | ROI | Tier | Checked |
|---|---|---:|---:|---:|---:|---|
| `error-boundaries` | Error boundaries + retry | 4 | 1 | 4.0 | 2 | - |
| `starter-template` | Starter week template | 5 | 1 | 5.0 | 2 | - |
| `loading-skeletons` | Loading skeletons | 3 | 1 | 3.0 | 2 | - |

**Decisions honored:** WF-001 · **Filtered (anti-bloat):** team workspaces

## Session Plan
<!-- apex:sessions:start -->
<!-- apex:sessions:end -->

## Questions for the owner
- Calendar sync: build now or defer?

## Next audit focus
- Onboarding funnel after S-005.
""")
print(cli("finalize-audit", "--date", "2026-10-12"))
sessions.set_status(p, "S-004", "done", today="2026-10-15T18:30:00")
sessions.set_status(p, "S-005", "done", today="2026-10-20T09:45:00")
sessions.set_status(p, "S-006", "dropped", notes="Superseded by streaming in S-008 (audit 2026-11-07)")

# ---------- Audit 3 (current) -------------------------------------------
d3 = {"core_loop": 8.0, "data_integrity": 7.0, "ux_onboarding": 6.5, "code_health": 7.5,
      "resilience": 6.0, "performance": 6.5, "testing": 6.0, "security": 6.0}  # 6.825
for kw in [
    dict(id="S-007", slug="cmd-k-palette", title="Cmd+K command palette for clients, tasks, and weeks",
         targets="src/components/CommandPalette.tsx, src/hooks/useHotkeys.ts, src/app/layout.tsx",
         patterns="src/components/ClientPicker.tsx", dod="pnpm run test -- CommandPalette", sha="c47e9f2", opp="cmd-k-palette",
         goal="Jump to any client, task, or week in two keystrokes.",
         context="Boardly reviewers repeatedly ask for keyboard navigation (reviews.example.com). Our power users plan on Mondays with both hands on the keyboard.",
         steps="1. `useHotkeys` hook (mirror `ClientPicker` focus handling).\n2. Palette with fuzzy search over clients/tasks/weeks.\n3. Mount in root layout.",
         flow="Press ⌘K → type 'acme' → Enter opens that client.", risk="Low; palette is additive. Revert the three files."),
    dict(id="S-008", slug="optimistic-task-moves", title="Optimistic drag-to-reschedule with instant undo",
         targets="src/app/planner/actions.ts, src/components/WeekGrid.tsx, src/components/UndoToast.tsx",
         patterns="src/app/clients/actions.ts", dod="pnpm run test -- WeekGrid", sha="c47e9f2", opp="optimistic-reschedule",
         model="opus", est=2, goal="Rescheduling feels instant and is always reversible.",
         context="Each drag waits ~400ms for the server (`src/app/planner/actions.ts:44`). Acme's top complaint is 'laggy drag and drop'.",
         steps="1. `useOptimistic` in WeekGrid.\n2. Server action returns canonical state; reconcile.\n3. UndoToast with 5s window.",
         flow="Drag a task to Thursday → moves instantly → Undo restores it; offline → toast explains and reverts.",
         risk="Medium: race conditions on rapid drags. Feature-flag `optimisticMoves`."),
    dict(id="S-009", slug="ci-health-workflow", title="GitHub Actions CI running typecheck, lint, and tests",
         targets=".github/workflows/ci.yml", patterns="package.json", dod="pnpm run lint", sha="c47e9f2",
         opp="ci-pipeline", est=0.75, goal="Every PR proves the build is green.",
         context="Health checks only run locally today; two regressions in October reached main.",
         steps="1. Workflow with pnpm cache running the four health checks.", flow="Open a PR → CI runs and reports.", risk="None."),
    dict(id="S-010", slug="planner-query-batching", title="Batch planner queries to remove the N+1 on week load",
         targets="src/lib/planner-data.ts, src/app/planner/page.tsx", patterns="src/lib/client-data.ts",
         dod="pnpm run test -- planner-data", sha="c47e9f2", opp="planner-n-plus-one", parallel="depends", deps="S-008",
         goal="Week view loads in one query instead of one per client.",
         context="`src/lib/planner-data.ts:27` loops clients and queries tasks per client (8 clients → 9 queries).",
         steps="1. Single `findMany` with `in` + group in memory.\n2. Keep the public function signature.",
         flow="Load a week with 8 clients; Prisma log shows 2 queries.", risk="Low; covered by planner tests.",
         ),
]:
    packet(**kw)
sessions.set_status(p, "S-007", "in_progress", today="2026-11-08T08:55:00")
roadmap(CARD(date="2026-11-07", mode="standard", sha="c47e9f2", overall=6.8, confidence="medium", research="full",
             health={"status": "pass"}, dimensions=d3,
             delta_justification="+1.7: S-004 and S-005 shipped (error boundaries, starter week cut onboarding from 6 to 2 steps), CI-ready test suite grew from 19 to 47 tests, and data layer gained transactions in src/lib/planner-data.ts:61."), """
> **North Star:** freelancers plan a realistic multi-client week in <60s · see `north-star.md`
> **Score 6.8 / 10 · Tier 2 · Reliability.** Reliable and pleasant for early adopters; now win on speed and keyboard flow where both competitors are weak.

## Scorecard
| Dimension | Weight | Score | Confidence | Evidence |
|---|---:|---:|---|---|
| Core loop & functionality | 20 | 8.0 | high | starter week → plan in 2 steps `src/app/onboarding/page.tsx:22`; overbooking banner `src/lib/planner.ts:131` |
| Data & schema integrity | 15 | 7.0 | high | zod at boundaries; transactions `src/lib/planner-data.ts:61` |
| UX states & onboarding | 15 | 6.5 | high | error boundaries (S-004); skeletons still missing on planner |
| Type safety & code health | 10 | 7.5 | high | strict TS, 3 `as any` left `src/lib/legacy-import.ts` |
| Error handling & resilience | 10 | 6.0 | medium | retry UI; no offline handling for drags |
| Performance | 10 | 6.5 | medium | N+1 on week load `src/lib/planner-data.ts:27` |
| Tests & CI | 10 | 6.0 | high | 47 tests pass; no CI workflow |
| Security & privacy | 10 | 6.0 | medium | authZ on all mutations; no rate limit on `/api/auth` |

### Score trend
<!-- apex:trend:start -->
<!-- apex:trend:end -->

## Health Check
| Check | Result | Notes |
|---|---|---|
| typecheck (`pnpm exec tsc --noEmit`) | pass | 0 errors |
| lint (`pnpm run lint`) | pass | 0 warnings |
| test (`pnpm run test`) | pass | 47 passed |
| build (`pnpm run build`) | pass | 41s |

## Progress Since Last Audit
- **Commits:** 23 since `8b21d0a` · **Sessions done:** S-004, S-005 · **Dropped:** S-006 (superseded by S-008's streaming approach)
- **Plan vs. actual:** 2 of 3 planned sessions shipped; off-plan work added transactions to the data layer (good call).
- **Regressions:** none.

## First 60 Seconds
1. Sign-up (email + password) → 2. **"Start with sample week"** → planner with a populated week.
- Steps to first value: **2** (Acme Tasks: 3, Boardly: 4) · Remaining friction: sample data can't be cleared in one click.

## Parity Matrix
| Workflow | Competitor | Verdict | Evidence | Source | Verified | Checked |
|---|---|---|---|---|---|---|
| Weekly planning | Acme Tasks (fictional) | Matches | Both offer a week grid | https://acmetasks.example.com/features | verified | 2026-11-07 |
| Overbooking warning | Acme Tasks (fictional) | Beats | No capacity model on their side | https://forum.example.com/t/acme-tasks-weekly-planning-is-painful/4411 | verified | 2026-11-07 |
| Starter templates | Boardly (fictional) | Matches | Both seed a sample workspace | https://boardly.example.com/templates | verified | 2026-11-07 |
| Keyboard navigation | Boardly (fictional) | Missing | Neither of us has a palette; their users ask for it | https://reviews.example.com/boardly/cons | verified | 2026-11-07 |
| Free tier limits | Acme Tasks (fictional) | Matches | Similar 3-project cap | https://acmetasks.example.com/pricing | verified | 2026-11-07 |
| Offline drag & drop | Boardly (fictional) | Missing | Not verified this run | - | unverified | 2026-11-07 |

### Competitor weaknesses we can exploit
- **Acme Tasks:** drag-and-drop is described as "laggy" (forum thread) → optimistic moves + instant undo (S-008).
- **Boardly:** no keyboard-first flow in reviews' "cons" → Cmd+K palette (S-007).

## Opportunities
| Slug | Opportunity | Impact | Effort (sessions) | ROI | Tier | Checked |
|---|---|---:|---:|---:|---:|---|
| `cmd-k-palette` | Cmd+K command palette | 4 | 1 | 4.0 | 3 | - |
| `ci-pipeline` | CI for health checks | 3 | 0.5 | 6.0 | 2 | - |
| `optimistic-reschedule` | Optimistic reschedule + undo | 5 | 1.5 | 3.3 | 2 | - |
| `planner-n-plus-one` | Batch planner queries | 3 | 1 | 3.0 | 2 | - |

**Filtered out (anti-bloat):** team workspaces, Zapier integration · **Decisions honored:** WF-001 (SSO), DF-001 (calendar sync, revisit 2027-01-15)

## Session Plan
<!-- apex:sessions:start -->
<!-- apex:sessions:end -->

## Questions for the owner
- Should sample data auto-expire after the first real client is added?

## Next audit focus
- Re-verify drag latency after S-008; spot-check `src/lib/legacy-import.ts`.
""")
print(cli("finalize-audit", "--date", "2026-11-07"))
w(".apex/research/competitors.md", """
# Competitor Research (fictional demo)
refreshed: 2026-11-07

## Acme Tasks (fictional)
- Positioning: general task manager with a weekly view.
- Core workflow: week grid with drag-and-drop (source: https://acmetasks.example.com/features)
- Top complaints: "laggy drag and drop", weekly setup takes too long (source: https://forum.example.com/t/acme-tasks-weekly-planning-is-painful/4411)
- Where we win: capacity/overbooking model, faster first plan.

## Boardly (fictional)
- Positioning: kanban boards with templates (source: https://boardly.example.com/templates)
- Top complaints: no keyboard navigation (source: https://reviews.example.com/boardly/cons)
- Where we win: keyboard-first planning (Cmd+K), week-centric view.
""")
print(cli("lint"))

# Demo lives inside the Apex repo, so finalize recorded that repo's HEAD; use each audit's own SHA instead.
import glob, subprocess as _sp
real = _sp.run(["git", "-C", WORK, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
shas = {"2026-09-14": "3f9c2e1", "2026-10-12": "8b21d0a", "2026-11-07": "c47e9f2"}
st = json.load(open(p.state))
for h in st["history"]:
    h["sha"] = shas[h["date"]]
st["last_audit_sha"] = shas[st["last_audit_date"]]
open(p.state, "w").write(json.dumps(st, indent=2) + "\n")
for f in glob.glob(os.path.join(p.history_dir, "*.md")):
    d = os.path.basename(f)[:10]
    s = open(f).read().replace(real, shas[d])
    open(f, "w").write(s)
w("README.md", """
# Demo: Tasklane (fictional)

A complete `.apex/` workspace for a **fictional** product, so you can try the Apex
CLI without installing anything or spending a single token. Competitors and URLs are
made up (`*.example.com`). The state, history snapshots, trend chart, and session
graph were produced by the real `apex.py` CLI across three simulated audits:

| Audit | Score | Tier | What happened |
|-------|------:|------|---------------|
| 2026-09-14 | 3.8 | 1 · Foundations | First full audit: unvalidated inputs, no strict types, no planner tests |
| 2026-10-12 | 5.1 | 2 · Reliability | S-001 to S-003 shipped; promoted past the +0.3 hysteresis band |
| 2026-11-07 | 6.8 | 2 · Reliability | +1.7 jump, so the linter required a written `delta_justification` |

```bash
python3 ../../scripts/apex.py status --project-dir .
python3 ../../scripts/apex.py lint --project-dir .
python3 ../../scripts/apex.py session next --project-dir .
```

Start with `.apex/roadmap.md`, then open a packet such as
`.apex/sessions/S-008-optimistic-task-moves.md`.
""")
print(cli("lint"))

shutil.rmtree(OUT, ignore_errors=True)
shutil.copytree(DEMO, OUT)
shutil.rmtree(WORK, ignore_errors=True)
print(f"demo written to {OUT}")
