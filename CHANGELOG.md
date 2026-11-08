# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: [SemVer](https://semver.org/).

## [0.1.0] — 2026-11-08
### Added
- `apex-auditor` subagent (Opus, high effort, project memory, 50-turn budget, delta mode).
- Skills: `/apex:init`, `/apex:audit` (`quick` | `standard` | `full`), `/apex:run-session`, `/apex:status`, `/apex:defer`.
- `apex.py` stdlib CLI: init, detect (JS/TS + Python), health, status, lint, finalize-audit, lock, decision, session, migrate.
- Hooks: write/Bash/read guards for the auditor, protection of Apex-managed files for all agents, URL provenance logging, a lint gate on SubagentStop, and a SessionStart banner.
- 8-dimension weighted rubric with a broken-build cap, ±0.3 tier hysteresis, Mermaid score trend and session graph, and immutable history snapshots.
- Zero-token demo (`examples/demo-saas`), Codex installer (prompt-only mode), and docs.
