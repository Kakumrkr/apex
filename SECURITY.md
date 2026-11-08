# Security Policy

## Reporting a vulnerability
Please **don't** open a public issue for security problems. Use GitHub's
[private vulnerability reporting](https://github.com/Kakumrkr/apex/security/advisories/new)
instead. Include steps to reproduce and the Claude Code version. You'll get a reply within 7 days.

Especially welcome:
- a command that `guard-bash` allows but that modifies files or runs arbitrary code
- a path that escapes the `guard-writes` allowlist
- a way to get a fabricated URL past the provenance check

## Supported versions
Only the latest release receives fixes.

## Threat model
See [docs/security.md](docs/security.md) for what Apex defends against and its known limits.
