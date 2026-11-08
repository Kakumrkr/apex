"""Secret-file detection (for read guards) and secret-pattern scanning (for lint)."""
from __future__ import annotations

import fnmatch
import os
import re

SECRET_FILE_GLOBS = (
    ".env", ".env.*", "*.env", ".envrc", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore",
    "id_rsa*", "id_dsa*", "id_ecdsa*", "id_ed25519*", "*.ppk", "credentials", "credentials.json",
    "service-account*.json", "*serviceaccount*.json", "*.tfstate", "*.tfvars", ".npmrc", ".pypirc",
    ".netrc", "_netrc", ".git-credentials", "secrets.json", "secrets.yml", "secrets.yaml", "secrets.toml",
    ".htpasswd", "*.kdbx",
)
SAFE_SUFFIXES = (".example", ".sample", ".template", ".dist", ".defaults")


def is_secret_path(path: str) -> bool:
    base = os.path.basename(str(path).rstrip("/\\")).lower()
    if not base or base.endswith(SAFE_SUFFIXES):
        return False
    return any(fnmatch.fnmatch(base, g) for g in SECRET_FILE_GLOBS)


SECRET_PATTERNS = (
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("Stripe live key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Private key block", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Connection string with password", re.compile(r"\b[a-z][a-z0-9+]*://[^\s:/@]+:[^\s@/]{6,}@[^\s]+", re.I)),
    ("Hard-coded credential", re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
)
_PLACEHOLDER = re.compile(r"(?i)(x{6,}|\*{4,}|<[^>]+>|example|changeme|your[_-]|placeholder|redacted|dummy)")


def scan_text(text: str) -> list[tuple[str, int, str]]:
    """Return (kind, line_no, redacted_snippet) for likely secrets."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for kind, rx in SECRET_PATTERNS:
            m = rx.search(line)
            if m and not _PLACEHOLDER.search(m.group(0)):
                val = m.group(0)
                hits.append((kind, i, val[:6] + "…" + f"({len(val)} chars)"))
    return hits
