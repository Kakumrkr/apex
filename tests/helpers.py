"""Shared fixtures: build a valid `.apex/` project in a temp dir."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
APEX_PY = os.path.join(SCRIPTS, "apex.py")
sys.path.insert(0, SCRIPTS)

from apex_core.paths import ApexPaths  # noqa: E402

DIMS = {"core_loop": 7.0, "data_integrity": 6.5, "ux_onboarding": 6.0, "code_health": 7.0,
        "resilience": 5.5, "performance": 6.5, "testing": 5.0, "security": 6.5}  # weighted = 6.325

SCORECARD = {"date": "2026-11-01", "mode": "full", "sha": "abc1234", "overall": 6.3, "confidence": "medium",
             "research": "full", "dimensions": DIMS, "health": {"status": "pass"}}


def roadmap(card=None, parity_rows=None, opp_rows=None, extra=""):
    card = card or SCORECARD
    parity_rows = parity_rows if parity_rows is not None else [
        "| Quick capture | Acme Tasks | Matches | Both support inbox capture | https://acme.example.com/features | verified | 2026-11-01 |",
        "| Offline mode | Boardly | Missing | Boardly works offline | - | unverified | 2026-11-01 |",
    ]
    opp_rows = opp_rows if opp_rows is not None else [
        "| `error-boundaries` | Error boundaries on dashboard | 4 | 1 | 4.0 | 2 | - |",
        "| `cmd-k-palette` | Cmd+K command palette | 4 | 1 | 4.0 | 3 | - |",
    ]
    return textwrap.dedent("""\
        # Apex Roadmap: Demo

        <!-- apex:scorecard {card} -->

        ## Scorecard
        | Dimension | Score |
        |---|---|
        | Core loop | 7.0 |

        ## Health Check
        All checks pass.

        ## Progress Since Last Audit
        First audit.

        ## First 60 Seconds
        Four steps to first value.

        ## Parity Matrix
        | Workflow | Competitor | Verdict | Evidence | Source | Verified | Checked |
        |---|---|---|---|---|---|---|
        {parity}

        ## Opportunities
        | Slug | Opportunity | Impact | Effort (sessions) | ROI | Tier | Checked |
        |---|---|---|---|---|---|---|
        {opps}

        ## Session Plan
        <!-- apex:sessions:start -->
        <!-- apex:sessions:end -->
        {extra}
        """).format(card=json.dumps(card), parity="\n".join(parity_rows), opps="\n".join(opp_rows), extra=extra)


def packet(sid="S-001", slug="add-error-boundaries", status="todo", parallel="safe", depends=None,
           targets=None, opportunity="error-boundaries", estimate=1.5, model="sonnet", body_extra=""):
    targets = targets or ["src/app/dashboard/error.tsx"]
    return textwrap.dedent(f"""\
        ---
        id: {sid}
        slug: {slug}
        title: Add error boundaries
        status: {status}
        model: {model}
        parallel: {parallel}
        depends_on: [{', '.join(depends or [])}]
        targets: [{', '.join(targets)}]
        patterns: [src/app/settings/error.tsx]
        do_not_touch: [prisma/schema.prisma]
        estimate_hours: {estimate}
        dod:
          - npx --no-install tsc --noEmit
        planned_at_sha: abc1234
        opportunity: {opportunity}
        ---
        ## Goal
        Stop white screens.
        ## Context
        Dashboard has no error boundary.
        ## Steps
        1. Add error.tsx
        ## Definition of Done
        Typecheck passes.
        ## Risk & Rollback
        Low; revert the file.
        ## Ready-to-run prompt
        Run /apex:run-session {sid}
        {body_extra}""")


def git(root, *args):
    subprocess.run(["git", "-C", root, *args], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                            GIT_COMMITTER_EMAIL="t@t"))


class ProjectCase(unittest.TestCase):
    use_git = False

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="apex-test-")
        self.p = ApexPaths(os.path.realpath(self.tmp))
        self.build()
        if self.use_git:
            git(self.tmp, "init", "-q")
            git(self.tmp, "add", "-A")
            git(self.tmp, "commit", "-q", "-m", "init")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel, text):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def build(self):
        self.write(".apex/north-star.md", "# Product North Star\n\n**Product:** Demo\n")
        self.write(".apex/decisions.md", textwrap.dedent("""\
            # Decisions
            | ID | Type | Slug | Title | Reason | Date | Revisit |
            |----|------|------|-------|--------|------|---------|
            | WF-001 | wont-fix | `sso-login` | SSO | Not our audience | 2026-10-01 | - |
            | DF-001 | deferred | `offline-mode` | Offline | Later | 2026-10-01 | 2026-10-15 |
            """))
        self.write(".apex/config.json", json.dumps({"schema_version": 1, "health_checks": []}))
        self.write(".apex/state.json", json.dumps({"schema_version": 1}))
        self.write(".apex/roadmap.md", roadmap())
        self.write(".apex/.search-log.json", json.dumps({"urls": {"https://acme.example.com/features": {}}}))
        self.write(".apex/sessions/S-001-add-error-boundaries.md", packet())
        self.write(".apex/sessions/S-002-cmd-k-palette.md",
                   packet("S-002", "cmd-k-palette", parallel="depends", depends=["S-001"],
                          targets=["src/components/CommandPalette.tsx"], opportunity="cmd-k-palette"))

    def read(self, rel):
        with open(os.path.join(self.tmp, rel), encoding="utf-8") as fh:
            return fh.read()

    def read_json(self, rel):
        return json.loads(self.read(rel))

    def run_cli(self, *args, stdin=None, env=None):
        return subprocess.run([sys.executable, APEX_PY, *args, "--project-dir", self.tmp],
                              input=stdin, capture_output=True, text=True, env=env)
