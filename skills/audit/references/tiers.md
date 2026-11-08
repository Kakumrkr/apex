# Maturity Tiers

The tier comes from `state.json` (computed by `apex.py finalize-audit` with ±0.3
hysteresis, so a project hovering at a boundary doesn't flip-flop). Plan for the
**current** tier. You may include at most one item from the next tier if its
ROI is exceptional.

| Tier | Score | Focus | Allowed opportunity types | Research depth |
|------|-------|-------|---------------------------|----------------|
| 1 · Foundations | 1.0–4.5 | Core loop, data/schema stability, type safety, a green build | Fix crashes, finish the core loop, schema/validation, typing, minimal tests on the critical path | **Light:** confirm the North Star competitors' core workflow only (≤4 searches). No polish. |
| 2 · Reliability | 4.6–7.5 | UX states, error boundaries, edge cases, onboarding friction | Loading skeletons, empty/error states, error boundaries, retries, onboarding step cuts, perf hot spots | **Full** parity matrix + weakness mining. Micro-delighters only if ≤1 session. |
| 3 · Market leader | 7.6–10.0 | Differentiation and craft | 10x differentiators from competitor weaknesses, micro-delighters (Cmd+K, optimistic UI, instant undo, shortcuts, zero-state polish), growth loops | **Full** + deep weakness mining across reviews/forums. |

## Anti-bloat filter (all tiers)
Reject or deprioritize, unless the North Star audience explicitly needs them:
SSO/SAML, RBAC matrices, multi-tenancy, audit logs, admin consoles, i18n before
product-market fit, plugin systems, custom theming engines, and "AI features" with
no tie to the core loop. A feature must serve the North Star audience's core
value proposition, or it doesn't make the list.

## ROI
`ROI = Impact (1-5) ÷ Effort (sessions)`. Rank by ROI, then by tier fit. Effort is
in 1-2 hour sessions; anything over 3 sessions must be split into several
opportunities.
