# Contributing to Apex

Thanks for helping! Apex is a Claude Code plugin with a dependency-free Python core.

## Setup
```bash
git clone https://github.com/Kakumrkr/apex.git && cd apex
python3 -m unittest discover tests -v            # Python 3.9+, no installs
python3 scripts/apex.py status --project-dir examples/demo-saas
claude plugin validate .                          # if Claude Code is installed
claude --plugin-dir .                             # try the plugin locally
```

## Ground rules
- **Stdlib only** in `scripts/`. Hooks run on every tool call, so keep them fast (the non-auditor path is ~25 ms).
- **Security changes need tests.** New allowlisted Bash commands go in `tests/test_guards.py` (ALLOW *and* DENY cases).
- **Determinism belongs in `apex.py`, judgment in prompts.** If the model keeps getting something mechanical wrong, move it into the CLI or the linter.
- Keep skill and agent prompts tight. Every always-on token is paid in every session (`claude plugin details apex`).
- Run `python3 scripts/apex.py lint --project-dir examples/demo-saas` before opening a PR.

## Good first issues
- Health-check detection for Go (`go vet`, `go test`) or Rust (`cargo check`, `cargo test`)
- Configurable rubric weights in `config.json`
- An optional Playwright walkthrough for the "First 60 Seconds" audit

## Commit style
Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
