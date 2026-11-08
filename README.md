<p align="center">
  <img src=".claude-plugin/icon.png" width="96" alt="Apex logo">
</p>

<h1 align="center">Apex</h1>

<p align="center">
  <b>Your repo's staff engineer. It audits, benchmarks, and plans, and never touches your code.</b><br>
  A Claude Code plugin that scores your project 1.0-10.0 with evidence, mines competitors' weaknesses,<br>
  and keeps a living roadmap of 1-2 hour sessions you can run one command at a time.
</p>

<p align="center">
  <a href="https://github.com/Kakumrkr/apex/actions/workflows/ci.yml?query=branch%3Amain"><img src="https://img.shields.io/github/actions/workflow/status/Kakumrkr/apex/ci.yml?branch=main&label=CI" alt="CI status"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-7c3aed" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/python-3.9%2B%20%C2%B7%20stdlib%20only-3776ab" alt="Python 3.9+, stdlib only">
</p>

---

## Why Apex?

AI coding agents are great at *doing* work and bad at deciding *which* work matters.
They forget what you rejected last week, score your project differently every
time you ask, and will happily "improve" your code while they're supposed to be reviewing it.

Apex fixes that with a strict separation of concerns:

- 🔍 **An auditor that can't write code.** Hooks restrict it to `.apex/` files and a read-only Bash allowlist. This is enforced, not just requested in the prompt.
- 📏 **A score you can trust.** 8 weighted dimensions, each backed by `file:line` evidence, recomputed by a linter. A broken build caps the score at 4.5.
- 🌐 **Competitor research that can't be invented.** Every "verified" claim must cite a URL the agent actually saw.
- 🧠 **Memory of your decisions.** Won't-fix and deferred ideas are never re-suggested and never cost you points.
- 🧩 **Sessions you can finish.** 1-2 hour packets with target files, patterns to mirror, do-not-touch lists, Definition-of-Done commands, and parallel-safety tags.

## Install

In Claude Code (2.1.275+):

```text
/plugin install apex --marketplace Kakumrkr/apex
```

Or in two steps:

```text
/plugin marketplace add Kakumrkr/apex
/plugin install apex@kakumrkr
```

**Requirements:** `git` and `python3` (3.9+) on your `PATH`. No pip installs.
**Auto-detected stacks:** JavaScript/TypeScript (npm, pnpm, yarn, bun) and Python. Other stacks can add checks to `config.json` by hand.

## The workflow

```mermaid
%%{init: {"htmlLabels": false, "flowchart": {"htmlLabels": false, "padding": 20}}}%%
flowchart LR
    A["/apex:init\nlock your North Star"] --> B["/apex:audit\nscore, benchmark, plan"]
    B --> C{"triage\nkeep, defer, won't fix"}
    C --> D["/apex:run-session S-001\nimplement, verify, commit"]
    D --> E["/apex:run-session S-002\nand so on"]
    E -->|"days or weeks later"| B
```

| Command | What it does | Model |
|---|---|---|
| `/apex:init` | Interviews you to lock the **Product North Star** (audience, value prop, competitors, non-goals) and confirms which health checks Apex may run. | your session |
| `/apex:audit [quick\|standard\|full]` | Progress review since the last audit → real health checks → rubric score → competitor research → roadmap + session packets → **interactive triage**. | Opus · high (`quick`: Sonnet, no web) |
| `/apex:run-session <id> [--branch\|--worktree]` | Preflight → implement inside the packet's targets → run its Definition of Done → mark done → atomic commit. | your session (packets recommend Sonnet or Opus) |
| `/apex:status` | Dashboard: score trend, tier, dimensions, sessions ready to run in parallel. | Sonnet · low |
| `/apex:defer <idea\|id>` | Records a Won't Fix / Deferred decision so audits respect it forever. | your session |
| `/apex:doctor` | Checks Python and git, plugin wiring, Claude Code settings, and `.apex/` integrity, and fires each guardrail hook live to prove it blocks what it should. | Sonnet · low |

## Try it now, with zero tokens

The repo ships a fully worked example: a fictional SaaS taken through three audits by the real CLI.

```bash
git clone https://github.com/Kakumrkr/apex.git && cd apex
python3 scripts/apex.py status --project-dir examples/demo-saas
```

```text
APEX · Tasklane (fictional demo)

Score   6.8 / 10  ▲ +1.7 since 2026-10-12
Tier    Tier 2 · Reliability (UX states, errors, edge cases)
Trend   ▃▄▆  (3 audits)
Audit   2026-11-07 (1d ago) · standard · c47e9f2

Dimensions
  Core loop & functionality      ████████░░ 8.0
  Data & schema integrity        ███████░░░ 7.0
  UX states & onboarding         ███████░░░ 6.5
  Type safety & code health      ████████░░ 7.5
  Error handling & resilience    ██████░░░░ 6.0
  Performance                    ███████░░░ 6.5
  Tests & CI                     ██████░░░░ 6.0
  Security & privacy             ██████░░░░ 6.0

Sessions  5 done · 1 in progress · 3 todo · 0 blocked · 1 dropped
  ▶ in progress: S-007 Cmd+K command palette for clients, tasks, and weeks
  Ready now:
    S-008  Optimistic drag-to-reschedule with instant undo  [Opus · Parallel-Safe · ~2h]
    S-009  GitHub Actions CI running typecheck, lint, and tests  [Sonnet · Parallel-Safe · ~0.75h]
  Run in parallel (git worktrees): S-008, S-009
  Next: /apex:run-session S-008

Decisions  1 won't-fix · 1 deferred
```

The same audits produce charts that GitHub renders straight from `.apex/roadmap.md`:

```mermaid
xychart-beta
    title "Tasklane: Apex score over three audits"
    x-axis ["Sep 14", "Oct 12", "Nov 07"]
    y-axis "Score" 0 --> 10
    line [3.8, 5.1, 6.8]
```

```mermaid
%%{init: {"htmlLabels": false, "flowchart": {"htmlLabels": false, "padding": 20}}}%%
flowchart LR
    S001["S-001\nValidate task + client inputs with zod at the API boundary"]:::done
    S002["S-002\nTurn on strict mode and fix the core-loop types"]:::done
    S003["S-003\nAdd tests for the weekly planner's capacity math"]:::done
    S004["S-004\nError boundaries + retry on the dashboard and planner"]:::done
    S005["S-005\nSeed a starter week so new users see value instantly"]:::done
    S007["S-007\nCmd+K command palette for clients, tasks, and weeks"]:::in_progress
    S008["S-008\nOptimistic drag-to-reschedule with instant undo"]:::todo
    S009["S-009\nGitHub Actions CI running typecheck, lint, and tests"]:::todo
    S010["S-010\nBatch planner queries to remove the N+1 on week load"]:::todo
    S008 --> S010
    classDef done fill:#d1fae5,stroke:#059669,color:#064e3b
    classDef in_progress fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef todo fill:#f3f4f6,stroke:#6b7280,color:#111827
```

Now watch the linter catch an auditor that inflates the score, fabricates a source, and re-proposes something you rejected:

```text
$ python3 scripts/apex.py lint --project-dir <tampered copy of the demo>
ERROR score-math [.apex/roadmap.md]: overall 8.4 must equal the weighted rubric score 6.83 (±0.15)
ERROR provenance [.apex/roadmap.md]: row 6: https://boardly.example.com/blog/no-offline-support was never observed via WebSearch/WebFetch (not in .apex/.search-log.json or committed research). Mark it 'unverified' or fetch the page first.
ERROR wont-fix [.apex/roadmap.md]: 'sso-login' was rejected as WF-001 (Explicit non-goal: solo freelancers, not teams). Remove it.
apex lint: 3 error(s), 0 warning(s)
```

In a real audit, this same check runs as a `SubagentStop` hook, so the auditor **can't finish** until it fixes these.
Browse [`examples/demo-saas/.apex/roadmap.md`](examples/demo-saas/.apex/roadmap.md) for the full output: scorecard with evidence, parity matrix, opportunities, and packets.
The demo is reproducible: `python3 examples/generate_demo.py` rebuilds it with the real CLI.

## Field-tested

Apex was run end to end with headless Claude Code on a small TypeScript project:

| Step | Result | Time | Cost |
|---|---|---:|---:|
| `/apex:audit quick` (first audit) | 2.7/10, Tier 1, 4 packets; vacuous test suite flagged; lint passed on first finalize | 2m | $0.40 |
| `/apex:run-session S-001` | implemented inside targets, 5 real tests, DoD green, atomic `feat(apex): S-001 …` commit | 1m | $0.37 |
| `/apex:audit quick` (delta) | 3.3/10 (+0.6); credited S-001 *and* caught a side effect it introduced, then planned S-005 to fix it | 1.3m | $0.32 |
| `/apex:doctor` | 24 checks healthy, including a live self-test of every guardrail hook | 16s | $0.06 |

Across these runs the guards denied a heredoc edit, file redirection, and an unlisted `sed`, and the auditor adapted each time. No source file was changed by any audit.
Every false positive found in these runs (`2>&1;`, `sed -n 1,40p`, `ls .apex/*`) became a regression test.
Numbers are from `quick` mode on a tiny repo. `standard`/`full` audits on Opus with web research cost more.

## What an audit produces

```text
.apex/
├── north-star.md          🔒 your locked Product North Star
├── decisions.md           🔒 append-only Won't Fix (WF-###) / Deferred (DF-###) log
├── roadmap.md             score + evidence, health, progress review, First-60-Seconds,
│                             parity matrix, ROI-ranked opportunities, session plan
├── sessions/S-007-*.md    self-contained 1-2h context packets (status in frontmatter)
├── research/competitors.md  cached research with sources + refresh date
├── history/2026-11-07-audit.md  🔒 immutable snapshot of every audit
├── state.json             🔒 score history, tier, last audited commit
└── config.json            stack + the health checks you approved
```

🔒 = Claude's Write/Edit tools are blocked on these for **every** agent. Changes go through `apex.py`.

## How it works

<details>
<summary><b>Maturity tiers (with hysteresis)</b></summary>

| Tier | Score | Focus |
|---|---|---|
| 1 · Foundations | 1.0-4.5 | Core loop, schema stability, type safety, a green build. Light competitor check only, no polish. |
| 2 · Reliability | 4.6-7.5 | Loading/empty/error states, error boundaries, edge cases, onboarding friction. |
| 3 · Market leader | 7.6-10.0 | Differentiators from competitor weaknesses, micro-delighters (⌘K, optimistic UI, instant undo). |

You're promoted only at `floor + 0.3` and demoted only at `floor - 0.3`, so a project at 4.6 doesn't flip-flop between tiers.
An **anti-bloat filter** rejects SSO/RBAC/multi-tenancy-style work unless your North Star audience needs it.
</details>

<details>
<summary><b>The rubric</b></summary>

Core loop 20 · Data integrity 15 · UX & onboarding 15 · Code health 10 · Resilience 10 · Performance 10 · Tests & CI 10 · Security 10.

`overall` must equal the weighted mean (±0.15). If a *required* health check fails, `overall ≤ 4.5`.
A move of more than 1.5 points from the last audit needs a written `delta_justification`. Full anchors are in [`rubric.md`](skills/audit/references/rubric.md).
</details>

<details>
<summary><b>Delta mode: cheap repeat audits</b></summary>

After the first audit, the auditor:
- spends ~80% of its reading on `git diff <last_audit_sha>..HEAD`
- reuses its codebase map from project memory (`.claude/agent-memory/apex*/MEMORY.md`)
- spot-checks 2-3 untouched modules

Research is cached for 28 days. `/apex:audit full` forces a complete re-scan; `--refresh` forces new research.
</details>

<details>
<summary><b>Session Context Packets</b></summary>

Each packet is self-contained, so a fresh session can execute it cold. It lists:
- **targets** (≤5 files) and **patterns** (existing files to mirror for style)
- **do-not-touch** paths
- **model** tier: `Sonnet · Standard Execution` or `Opus · Deep Architecture`
- **dod** (verification commands) plus a manual flow
- **risk & rollback**
- a **ready-to-run prompt**
- a **parallel tag**

The linter guarantees `Parallel-Safe` packets share no target files, so you can run them simultaneously in git worktrees.
`/apex:run-session` commits atomically on your current branch by default; it never pushes.
</details>

<details>
<summary><b>Guardrails: what's enforced by code vs. prompts</b></summary>

| Guarantee | Enforced by |
|---|---|
| Auditor writes only `.apex/roadmap.md`, `sessions/`, `research/`, and its memory | `PreToolUse` hook |
| Auditor's Bash is a read-only allowlist, parsed by a quote-aware tokenizer (no file redirects, `git` writes, installs, `--fix`, `python -c`, `$VAR` or `$(...)`, globs or recursive greps that could reach `.env`) | `PreToolUse` hook |
| Auditor can't read `.env*`, keys, or credentials | `PreToolUse` hook |
| North Star, decisions, state, history, and evidence files are immutable to all agents | `PreToolUse` hook |
| "Verified" competitor URLs were actually observed | `PostToolUse` log + lint |
| Score math, health evidence, packet schema, no secrets in `.apex/` | `SubagentStop` lint gate |
| Done packets never change | lint (git HEAD comparison) |

Full threat model and known limits: [docs/security.md](docs/security.md).
</details>

## Troubleshooting

`/apex:doctor` (or `python3 scripts/apex.py doctor`) checks Python, git, plugin wiring, and your Claude Code settings.
It also fires each guardrail hook with a real event to prove it blocks what it should, then validates `.apex/`.
This is a real run on a project after three audits:

```text
$ python3 scripts/apex.py doctor
...
Guardrail self-test
  ✓ auditor `git push` is denied: 42 ms
  ✓ auditor `git log` is allowed: 38 ms
  ✓ auditor write to src/ is denied: 40 ms
  ✓ auditor read of .env is denied: 39 ms
  ✓ north-star.md is locked for everyone: 41 ms
  ✓ your own Bash is untouched: 28 ms

Claude Code settings
  ✓ settings: no settings files override hooks

Project (.apex/)
  ✓ git repository: HEAD d3787c3
  ✓ north-star.md: all 5 fields filled
  ✓ config.json: 2 health checks (1 required)
  ✓ state.json: tier 1, 3 audit(s)
  ✓ last audited commit: d3787c3 is reachable, so the next audit runs in delta mode
  ✓ history/: 3 immutable snapshot(s)
  ✓ decisions.md: 0 decision(s)
  ✓ .gitignore: runtime files ignored
  ✓ sessions: 1 done, 4 todo
  ✓ lint: no issues

24 checks · 0 failed · 0 warning(s) · healthy
```

A failure in "Guardrail self-test" or "Claude Code settings" (for example `disableAllHooks: true`) means audits are **not** read-only right now.

## Using Codex?

`scripts/install-codex.sh` installs the same skills into `.agents/skills` for OpenAI Codex, in **prompt-only mode** (no hooks there). See [docs/codex.md](docs/codex.md).

## Documentation

- [Architecture](docs/architecture.md): the judgment / bookkeeping / enforcement split, with diagrams
- [Security & threat model](docs/security.md)
- [FAQ](docs/faq.md): cost, stacks, Windows, parallel sessions
- [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## Development

```bash
python3 -m unittest discover tests -v     # 80+ tests, stdlib only
python3 scripts/apex.py doctor            # wiring + live guardrail self-test
claude plugin validate .                  # manifest, skills, agent, hooks
claude --plugin-dir .                     # load your working copy in Claude Code
```

## License

[MIT](LICENSE) © 2026 [Rama Kakumani](https://github.com/Kakumrkr)
