import json
import os

from helpers import ProjectCase


class Doctor(ProjectCase):
    use_git = True

    def doctor(self, *extra):
        env = dict(os.environ, HOME=self.tmp)  # isolate from the developer's ~/.claude/settings.json
        res = self.run_cli("doctor", "--json", *extra, env=env)
        data = json.loads(res.stdout)
        return res.returncode, {c["check"]: c for c in data["checks"]}, data

    def test_plugin_and_live_guardrails_pass(self):
        _, checks, _ = self.doctor()
        for name in ("plugin.json", "components", "hooks.json", "file permissions",
                     "auditor `git push` is denied", "auditor `git log` is allowed",
                     "auditor write to src/ is denied", "auditor read of .env is denied",
                     "north-star.md is locked for everyone", "your own Bash is untouched"):
            self.assertEqual(checks[name]["status"], "ok", (name, checks[name]))

    def test_disable_all_hooks_is_a_failure(self):
        self.write(".claude/settings.local.json", json.dumps({"disableAllHooks": True}))
        code, checks, data = self.doctor("--no-selftest")
        bad = [c for c in data["checks"] if c["check"].endswith("settings.local.json")]
        self.assertEqual(bad[0]["status"], "fail")
        self.assertIn("guardrail", bad[0]["detail"])
        self.assertEqual(code, 1)

    def test_project_integrity(self):
        self.write(".apex/config.json", "{not json")
        code, checks, _ = self.doctor("--no-selftest")
        self.assertEqual(checks["config.json"]["status"], "fail")
        self.assertEqual(checks["north-star.md"]["status"], "warn")  # fixture fills only **Product:**
        self.assertEqual(checks[".gitignore"]["status"], "warn")
        self.assertEqual(checks["runtime files"]["status"], "warn")  # fixture commits .search-log.json
        self.assertEqual(code, 1)

    def test_uninitialized_project_is_not_a_failure(self):
        import shutil
        shutil.rmtree(os.path.join(self.tmp, ".apex"))
        code, checks, _ = self.doctor("--no-selftest")
        self.assertEqual(checks[".apex/"]["status"], "warn")
        self.assertEqual(code, 0)

    def test_text_output(self):
        res = self.run_cli("doctor", "--no-selftest", env=dict(os.environ, HOME=self.tmp))
        self.assertIn("apex doctor", res.stdout)
        self.assertRegex(res.stdout, r"\d+ checks · \d+ failed")
