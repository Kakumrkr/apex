import json
import sys
import unittest

from helpers import ProjectCase
from apex_core import health


class Health(ProjectCase):
    def test_runner_statuses(self):
        py = sys.executable
        self.write(".apex/config.json", json.dumps({"health_checks": [
            {"name": "ok", "cmd": f"{py} -c \"print('fine')\"", "required": True, "timeout": 30},
            {"name": "lint", "cmd": f"{py} -c \"import sys; print('E1 bad'); sys.exit(1)\"", "required": False},
            {"name": "slow", "cmd": f"{py} -c \"import time; time.sleep(5)\"", "required": False, "timeout": 1},
            {"name": "missing", "cmd": "definitely-not-a-real-binary --x", "required": False},
        ]}))
        rep = health.run(self.p)
        by = {r["name"]: r for r in rep["results"]}
        self.assertEqual(by["ok"]["status"], "pass")
        self.assertEqual(by["lint"]["status"], "fail")
        self.assertIn("E1 bad", by["lint"]["tail"])
        self.assertEqual(by["slow"]["status"], "timeout")
        self.assertEqual(by["missing"]["status"], "error")
        self.assertEqual(rep["status"], "partial")
        self.assertEqual(self.read_json(".apex/.health.json")["status"], "partial")

    def test_required_failure_is_fail(self):
        py = sys.executable
        self.write(".apex/config.json", json.dumps({"health_checks": [
            {"name": "build", "cmd": f"{py} -c \"raise SystemExit(2)\"", "required": True}]}))
        self.assertEqual(health.run(self.p)["status"], "fail")

    def test_no_checks_is_skipped(self):
        self.assertEqual(health.run(self.p)["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
