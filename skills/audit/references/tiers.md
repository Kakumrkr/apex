# Maturity Tiers

The tier comes from `state.json` (computed by `apex.py finalize-audit` with ±0.3
hysteresis, so a project hovering at a boundary doesn't flip-flop). Plan for the
**current** tier. You may include at most one item from the next tier if its
ROI is exceptional, and you must label it `next-tier` in its rationale.

| Tier | Score | Focus | Allowed opportunity types | Research depth |
|------|-------|-------|---------------------------|----------------|
| 1 · Foundations | 1.0-4.5 | Core loop, data/schema stability, type safety, a green build | Fix crashes, finish the core loop, schema/validation, typing, minimal tests on the critical path | **Light:** confirm the North Star competitors' core workflow only (≤4 searches). No polish. |
| 2 · Reliability | 4.6-7.5 | UX states, error boundaries, edge cases, onboarding friction | Loading skeletons, empty/error states, error boundaries, retries, onboarding step cuts, perf hot spots | **Full** parity matrix + weakness mining. Micro-delighters only if ≤1 session. |
| 3 · Market leader | 7.6-10.0 | Differentiation and craft | 10x differentiators from competitor weaknesses, micro-delighters, growth loops | **Full** + deep weakness mining across reviews and forums. |

## Exit criteria (what "done with this tier" looks like)
Use these to pick the opportunities that move the project to the next tier.

**Leaving Tier 1** (all of):
- Every *required* health check passes on HEAD.
- The target user can complete the core loop end to end with no dead route,
  stub, or manual database step.
- Inputs that create or change data are validated at the boundary (zod,
  Pydantic, Django forms/serializers).
- At least one automated test exercises the core loop's happy path.
- TypeScript `strict` (or mypy/pyright on the core package) is on, even if a
  few modules are excluded.

**Leaving Tier 2** (all of):
- Every data-driven view has loading, empty, and error states.
- An error in one widget or request never blanks the whole page or crashes the CLI.
- Outbound calls have timeouts; retries are idempotent.
- A new user reaches first value in ≤60 seconds without reading docs (see the
  First 60 Seconds audit).
- CI runs the required checks on every push; the core loop has failure-path tests.
- AuthZ is enforced on every mutation; auth endpoints are rate limited.

**Staying in Tier 3:** at least one capability is measurably better than every
North Star competitor (cite the parity matrix), and micro-delighters cover the
three most frequent actions.

## Anti-bloat filter (all tiers)
Reject or deprioritize, unless the North Star audience explicitly needs them:
SSO/SAML, RBAC matrices, multi-tenancy, audit logs, admin consoles, i18n before
product-market fit, plugin systems, custom theming engines, and "AI features" with
no tie to the core loop. A feature must serve the North Star audience's core
value proposition, or it doesn't make the list.

Ask three questions of every candidate. If any answer is "no", drop it or
record why in the rationale:
1. Would the North Star audience notice within their first week?
2. Does it make the core loop faster, safer, or more trustworthy?
3. Is it the smallest version that proves the value (one or two sessions)?

## ROI
`ROI = Impact (1-5) ÷ Effort (sessions)`. Rank by ROI, then by tier fit. Effort is
in 1-2 hour sessions; anything over 3 sessions must be split into several
opportunities.

| Impact | Meaning |
|-------:|---------|
| 5 | Unblocks the core loop or removes a data-loss / security risk |
| 4 | Removes friction every user hits on most visits |
| 3 | Fixes a frequent edge case or a top competitor complaint |
| 2 | Polish a returning user notices |
| 1 | Nice to have |

When two items tie, prefer the one with stronger evidence (a failing health
check or a cited competitor complaint beats a hunch).

## Micro-delighter catalogue (Tier 2 if ≤1 session, otherwise Tier 3)
Each entry: how to detect it's missing, the implementation pattern to put in the
packet, the pitfall the packet's Definition of Done must cover, and a size.
Only propose the ones that touch the North Star's top three actions.

### 1. Command palette (⌘K / Ctrl+K)
- **Missing if:** `rg -n 'cmdk|kbar|CommandDialog|useHotkeys|metaKey' src` finds nothing.
- **Pattern (React):** `cmdk` (or shadcn `Command`) inside a dialog; a global
  `keydown` listener for `(e.metaKey || e.ctrlKey) && e.key === 'k'`; actions
  registered from a single `commands.ts` array (id, label, keywords, `run()`),
  plus recent items first. Navigation entries come from the router config, so
  new pages appear automatically.
- **Pitfalls:** don't hijack ⌘K inside text inputs that use it; trap focus;
  `Esc` closes and restores focus; announce results to screen readers.
- **Size:** 1 session for navigation + 5 actions.

### 2. Optimistic UI with rollback
- **Missing if:** mutations `await` the server before updating the list
  (`rg -n 'onMutate|useOptimistic|optimistic' src` is empty).
- **Pattern:** TanStack Query `onMutate` (cancel queries, snapshot, set data),
  `onError` (restore snapshot + toast), `onSettled` (invalidate). In Next.js App
  Router, `useOptimistic` + a Server Action. Generate client IDs (`crypto.randomUUID()`)
  so created rows are stable before the server responds.
- **Pitfalls:** server must be idempotent on retry (accept the client ID);
  reorder operations need a deterministic sort key.
- **Size:** 1 session per mutation family (create/update/move).

### 3. Instant undo (instead of "Are you sure?")
- **Missing if:** destructive actions use `confirm(` / confirmation modals:
  `rg -n 'confirm\(|AlertDialog|Are you sure' src`.
- **Pattern:** perform the delete optimistically and show a toast with "Undo"
  for 5-8 s. Either soft-delete (`deleted_at`, restored on undo, purged by a job)
  or defer the request until the toast expires. Keyboard: `⌘Z` triggers the
  latest undo.
- **Pitfalls:** navigation away must flush or keep the pending delete; undo must
  restore order and relations.
- **Size:** 1 session (soft-delete column adds a migration: note it in Risk).

### 4. Keyboard shortcuts for the top 3 actions
- **Missing if:** no `useHotkeys`/`keydown` handlers beyond forms.
- **Pattern:** single-key shortcuts outside inputs (`c` create, `/` search,
  `j`/`k` move, `e` edit), a `?` overlay listing them, `aria-keyshortcuts` on
  buttons, and the shortcut shown in tooltips.
- **Pitfalls:** ignore events from `input`, `textarea`, `[contenteditable]`;
  respect IME composition (`e.isComposing`).
- **Size:** ≤1 session.

### 5. Zero-state that teaches
- **Missing if:** empty lists render nothing or "No data".
- **Pattern:** empty state = one sentence of value + the primary action button +
  optional "Load sample data" that creates clearly-labelled demo records the
  user can delete in one click.
- **Pitfalls:** sample data must never mix with real exports or billing counts.
- **Size:** ≤1 session for the main view.

### 6. Skeletons that match the layout
- **Missing if:** spinners or blank areas while loading.
- **Pattern:** Next.js `loading.tsx` or `<Suspense fallback={<ListSkeleton/>}>`
  with skeletons that mirror the final layout (same row height, count from the
  last result or the page size) to avoid layout shift.
- **Size:** ≤1 session for the core routes.

### 7. Forgiving inputs
- **Pattern:** natural-language dates ("next fri"), paste-to-import (a list of
  lines becomes N items), drag-and-drop file upload with progress, autosave
  drafts to `localStorage` with "Restored your draft" notice.
- **Pitfalls:** show the parsed interpretation before saving; drafts keyed by
  user and record id.
- **Size:** 1 session each.

### 8. Shareable, restorable state
- **Pattern:** filters, sort, tabs and selected item live in the URL
  (`useSearchParams` / `nuqs`), so refresh and links restore the view; "Copy link"
  on any item.
- **Size:** ≤1 session.

### 9. Python CLI delighters
- **Did-you-mean:** on an unknown command or option, suggest the closest match
  (`difflib.get_close_matches`); click/typer get this cheaply.
- **Progress and timing:** `rich.progress` (or a simple spinner) for anything
  >1 s, and a one-line summary at the end ("Synced 42 items in 3.1s").
- **`--json` and `--quiet`:** machine-readable output and silent mode for scripts;
  non-zero exit codes for failure.
- **Dry runs:** `--dry-run` that prints the exact changes for any destructive command.
- **Shell completion:** `typer --install-completion` or click's completion docs
  in the README.
- **Fast `--help`:** import heavy modules lazily inside commands.
- **Size:** ≤1 session each.

### 10. Python web (Django / FastAPI) delighters
- **Instant feedback without a SPA:** htmx `hx-post` + `hx-swap` for inline edits
  and deletes with undo toasts (Django messages rendered as toasts).
- **Friendly errors:** custom 404/500 templates (Django) or exception handlers
  (FastAPI) returning `{ "error": { "code", "message", "hint" } }`.
- **Admin quality of life:** `list_display`, `search_fields`, `list_filter`,
  `autocomplete_fields` on the models the team touches daily (only if the
  North Star audience uses the admin).
- **API ergonomics:** consistent pagination (`cursor`/`next`), `ETag`/`If-None-Match`
  on read endpoints, and an OpenAPI example per endpoint.
