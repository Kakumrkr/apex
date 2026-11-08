import json
import os
import subprocess
import sys
import unittest

from helpers import APEX_PY, ProjectCase, roadmap, SCORECARD, DIMS
from apex_core import decisions, sessions
from apex_core.state import next_tier
from apex_core import fm, md


class Init(ProjectCase):
    def build(self):
        self.write("package.json", json.dumps({"scripts": {"lint": "eslint .", "test": "vitest run",
                                                          "dev": "next dev"},
                                              "devDependencies": {"typescript": "5", "next": "15"}}))
        self.write("pnpm-lock.yaml", "")

    def test_init_creates_workspace(self):
        spec = {"product": "Tasklane", "audience": "Freelancers", "value": "Plan a week in 60s",
                "competitors": ["Todoist", "Trello"], "non_goals": ["Enterprise SSO", "Native apps"]}
        res = self.run_cli("init", stdin=json.dumps(spec))
        self.assertEqual(res.returncode, 0, res.stderr)
        ns = self.read(".apex/north-star.md")
        for needle in ("**Target audience:** Freelancers", "**Top competitors:** Todoist, Trello",
                       "**Explicit non-goals:** Enterprise SSO; Native apps"):
            self.assertIn(needle, ns)
        cfg = self.read_json(".apex/config.json")
        cmds = [c["cmd"] for c in cfg["health_checks"]]
        self.assertIn("pnpm exec tsc --noEmit", cmds)
        self.assertIn("pnpm run lint", cmds)
        self.assertIn("typescript", cfg["stack"])
        self.assertIn(".apex/.search-log.json", self.read(".gitignore"))
        again = self.run_cli("init", stdin=json.dumps(spec))
        self.assertNotEqual(again.returncode, 0, "North Star must not be silently replaced")
        self.assertEqual(self.run_cli("init", "--force", stdin=json.dumps(spec)).returncode, 0)

    def test_init_requires_fields(self):
        res = self.run_cli("init", stdin=json.dumps({"audience": "x"}))
        self.assertEqual(res.returncode, 2)


class Detect(ProjectCase):
    def build(self):
        self.write("pyproject.toml", "[tool.ruff]\n[tool.mypy]\n[project]\ndependencies=['fastapi','pytest']\n")
        os.makedirs(os.path.join(self.tmp, "tests"))

    def test_python_detection(self):
        out = json.loads(self.run_cli("detect").stdout)
        names = {c["name"] for c in out["health_checks"]}
        self.assertTrue({"compile", "test", "lint", "typecheck"} <= names, names)
        self.assertIn("fastapi", out["stack"])


class Decisions(ProjectCase):
    def test_add_and_ids(self):
        d1 = decisions.add(self.p, "wont-fix", "Dark mode", "Not a priority", today="2026-11-08")
        self.assertEqual(d1["id"], "WF-002")
        d2 = decisions.add(self.p, "deferred", "Calendar sync", "After v1", revisit="2027-01-01")
        self.assertEqual(d2["id"], "DF-002")
        self.assertEqual(d2["slug"], "calendar-sync")
        with self.assertRaises(ValueError):
            decisions.add(self.p, "wont-fix", "Dark mode", "dup")
        with self.assertRaises(ValueError):
            decisions.add(self.p, "wont-fix", "No reason", "")
        slugs = [d["slug"] for d in decisions.load(self.p)]
        self.assertEqual(slugs, ["sso-login", "offline-mode", "dark-mode", "calendar-sync"])

    def test_titles_with_pipes_are_escaped(self):
        decisions.add(self.p, "wont-fix", "A | B", "x | y")
        self.assertEqual(decisions.load(self.p)[-1]["title"], "A | B")


class Sessions(ProjectCase):
    def test_status_flow(self):
        with self.assertRaises(ValueError):
            sessions.set_status(self.p, "S-002", "in_progress")  # depends on S-001
        sessions.set_status(self.p, "1", "in_progress")
        s = sessions.set_status(self.p, "S-001", "done")
        self.assertEqual(s["status"], "done")
        self.assertIn("completed_at", s)
        self.assertEqual([x["id"] for x in sessions.ready(sessions.load_all(self.p))], ["S-002"])
        with self.assertRaises(ValueError):
            sessions.set_status(self.p, "S-001", "todo")

    def test_set_status_preserves_body(self):
        before = self.read(".apex/sessions/S-001-add-error-boundaries.md")
        sessions.set_status(self.p, "S-001", "blocked", notes="tsc fails: missing types")
        after = self.read(".apex/sessions/S-001-add-error-boundaries.md")
        self.assertEqual(before.split("---", 2)[2], after.split("---", 2)[2])
        meta, _ = fm.parse(after)
        self.assertEqual(meta["notes"], "tsc fails: missing types")
        self.assertEqual(meta["dod"], ["npx --no-install tsc --noEmit"])


class Finalize(ProjectCase):
    def test_finalize_updates_state_and_history(self):
        res = self.run_cli("finalize-audit", "--date", "2026-11-01")
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        out = json.loads(res.stdout)
        self.assertEqual(out["score"], 6.3)
        self.assertEqual(out["tier"], 2)
        state = self.read_json(".apex/state.json")
        self.assertEqual(state["last_audit_date"], "2026-11-01")
        self.assertEqual(len(state["history"]), 1)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, ".apex/history/2026-11-01-audit.md")))
        rm = self.read(".apex/roadmap.md")
        self.assertIn("xychart-beta", rm)
        self.assertIn("flowchart LR", rm)
        # GitHub clips HTML labels; the session graph must use native SVG text.
        self.assertIn('%%{init: {"htmlLabels": false, "flowchart": {"htmlLabels": false', rm)
        self.assertNotIn("<br/>", rm)
        self.assertEqual(rm.count("<!-- apex:sessions:start -->"), 1)
        # second audit same day -> new snapshot, tier hysteresis applies
        dims = {k: 7.7 for k in DIMS}
        self.write(".apex/roadmap.md", roadmap(dict(SCORECARD, dimensions=dims, overall=7.7)))
        out2 = json.loads(self.run_cli("finalize-audit", "--date", "2026-11-01").stdout)
        self.assertEqual(out2["tier"], 2, "7.7 is inside the +0.3 band; stays Tier 2")
        self.assertTrue(os.path.exists(os.path.join(self.tmp, ".apex/history/2026-11-01-audit-2.md")))
        status = self.run_cli("status").stdout
        self.assertIn("Score   7.7 / 10", status)
        self.assertIn("▲ +1.4", status)

    def test_finalize_refuses_on_lint_errors(self):
        self.write(".apex/roadmap.md", roadmap(dict(SCORECARD, overall=9.9)))
        res = self.run_cli("finalize-audit")
        self.assertEqual(res.returncode, 2)
        self.assertIn("score-math", res.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, ".apex/history")) and
                         os.listdir(os.path.join(self.tmp, ".apex/history")))

    def test_lock(self):
        self.assertEqual(self.run_cli("lock", "acquire").returncode, 0)
        self.assertEqual(self.run_cli("lock", "acquire").returncode, 2)
        self.assertEqual(self.run_cli("lock", "release").returncode, 0)


class Hooks(ProjectCase):
    def hook(self, name, event):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.tmp)
        return subprocess.run([sys.executable, APEX_PY, "hook", name], input=json.dumps(event),
                              capture_output=True, text=True, env=env)

    def test_guard_writes_output_shape(self):
        res = self.hook("guard-writes", {"cwd": self.tmp, "agent_type": "apex-auditor", "tool_name": "Write",
                                         "tool_input": {"file_path": os.path.join(self.tmp, "src/a.ts")}})
        out = json.loads(res.stdout)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertEqual(out["hookEventName"], "PreToolUse")
        res = self.hook("guard-writes", {"cwd": self.tmp, "tool_name": "Write",
                                         "tool_input": {"file_path": "src/a.ts"}})
        self.assertEqual(res.stdout.strip(), "", "main thread writes get no opinion")

    def test_guard_bash_allows_health_check_exact(self):
        self.write(".apex/config.json", json.dumps({"health_checks": [{"name": "b", "cmd": "make check"}]}))
        res = self.hook("guard-bash", {"cwd": self.tmp, "agent_type": "apex-auditor", "tool_name": "Bash",
                                       "tool_input": {"command": "make check"}})
        self.assertEqual(json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"], "allow")

    def test_malformed_event_fails_open_for_users(self):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.tmp)
        res = subprocess.run([sys.executable, APEX_PY, "hook", "guard-bash"], input="not json",
                             capture_output=True, text=True, env=env)
        self.assertEqual((res.returncode, res.stdout), (0, ""))

    def test_search_log_records_urls(self):
        self.hook("search-log", {"cwd": self.tmp, "agent_type": "apex-auditor", "tool_name": "WebSearch",
                                 "tool_input": {"query": "acme reviews"},
                                 "tool_response": {"results": [{"url": "https://reddit.com/r/x/comments/1/acme_sucks/"}]}})
        log = self.read_json(".apex/.search-log.json")
        self.assertIn("https://reddit.com/r/x/comments/1/acme_sucks", log["urls"])
        self.hook("search-log", {"cwd": self.tmp, "agent_type": "general-purpose", "tool_name": "WebFetch",
                                 "tool_input": {"url": "https://ignored.example.com"}})
        log = self.read_json(".apex/.search-log.json")
        self.assertNotIn("https://ignored.example.com", log["urls"])

    def test_subagent_stop_blocks_on_errors(self):
        ok = self.hook("subagent-stop", {"cwd": self.tmp, "agent_type": "apex-auditor"})
        self.assertEqual(ok.stdout.strip(), "")
        self.write(".apex/roadmap.md", roadmap(dict(SCORECARD, overall=9.0)))
        bad = json.loads(self.hook("subagent-stop", {"cwd": self.tmp, "agent_type": "apex-auditor"}).stdout)
        self.assertEqual(bad["decision"], "block")
        self.assertIn("score-math", bad["reason"])
        other = self.hook("subagent-stop", {"cwd": self.tmp, "agent_type": "Explore"})
        self.assertEqual(other.stdout.strip(), "")

    def test_session_start_banner(self):
        self.run_cli("finalize-audit")
        out = self.hook("session-start", {"cwd": self.tmp}).stdout
        self.assertIn("Apex 6.3/10 (Tier 2)", out)
        self.assertIn("next: S-001", out)


class Units(unittest.TestCase):
    def test_tier_hysteresis(self):
        self.assertEqual(next_tier(4.6, None), 2)
        self.assertEqual(next_tier(4.7, 1), 1)
        self.assertEqual(next_tier(4.9, 1), 2)
        self.assertEqual(next_tier(4.4, 2), 2)
        self.assertEqual(next_tier(4.2, 2), 1)
        self.assertEqual(next_tier(9.0, 1), 3)
        self.assertEqual(next_tier(2.0, 3), 1)

    def test_frontmatter_roundtrip(self):
        text = "---\nid: S-001\nlist: [a, \"b, c\"]\nblock:\n  - x\n  - y\nn: 1.5\nflag: true\nempty:\n---\nbody"
        meta, body = fm.parse(text)
        self.assertEqual(meta, {"id": "S-001", "list": ["a", "b, c"], "block": ["x", "y"], "n": 1.5,
                                "flag": True, "empty": None})
        out = fm.set_fields(text, {"block": "done", "new": "a: b"})
        meta2, body2 = fm.parse(out)
        self.assertEqual((meta2["block"], meta2["new"], body2), ("done", "a: b", "body"))

    def test_md_tables_and_sections(self):
        text = "# T\n## A\n| X | Y |\n|---|---|\n| 1 | a \\| b |\n## B\n```\n## not a heading\n```\ntext"
        self.assertEqual(md.first_table(md.section(text, "A")), [{"x": "1", "y": "a | b"}])
        self.assertIn("not a heading", md.section(text, "B"))


if __name__ == "__main__":
    unittest.main()
