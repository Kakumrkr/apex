import unittest

from helpers import APEX_PY  # noqa: F401  (sets sys.path)
from apex_core import fm


def doc(*lines, nl="\n"):
    return nl.join(("---",) + lines + ("---", "body")) + nl


class Frontmatter(unittest.TestCase):
    def test_colons_in_quoted_and_plain_values(self):
        data, _ = fm.parse(doc('title: "Auth: Fix race condition"', "note: Auth: fix it",
                               "single: 'Ratio 1:2'", "url: https://example.com/a:b"))
        self.assertEqual(data["title"], "Auth: Fix race condition")
        self.assertEqual(data["note"], "Auth: fix it")
        self.assertEqual(data["single"], "Ratio 1:2")
        self.assertEqual(data["url"], "https://example.com/a:b")

    def test_inline_comments(self):
        data, _ = fm.parse(doc("status: todo # picked by run-session", 'title: "A # not a comment" # real one',
                               "estimate_hours: 1.5  # ~90 minutes", "depends_on: [S-001] # after S-001",
                               "targets:", "  - src/a.ts # primary", "anchor: page#section",
                               "# a full-line comment", "model: sonnet"))
        self.assertEqual(data["status"], "todo")
        self.assertEqual(data["title"], "A # not a comment")
        self.assertEqual(data["estimate_hours"], 1.5)
        self.assertEqual(data["depends_on"], ["S-001"])
        self.assertEqual(data["targets"], ["src/a.ts"])
        self.assertEqual(data["anchor"], "page#section")
        self.assertEqual(data["model"], "sonnet")

    def test_inline_and_block_lists(self):
        data, _ = fm.parse(doc("depends_on: [S-001, S-002]", 'patterns: ["src/a, b.ts", \'x.ts\']',
                               "empty: []", "targets:", "  - S-001", "  - S-002",
                               "dod:", "- npm test", '- "npx --no-install tsc --noEmit"', "next: 1"))
        self.assertEqual(data["depends_on"], ["S-001", "S-002"])
        self.assertEqual(data["patterns"], ["src/a, b.ts", "x.ts"])
        self.assertEqual(data["empty"], [])
        self.assertEqual(data["targets"], ["S-001", "S-002"])
        self.assertEqual(data["dod"], ["npm test", "npx --no-install tsc --noEmit"])
        self.assertEqual(data["next"], 1)

    def test_crlf_line_endings(self):
        text = doc("id: S-001", 'title: "Auth: Fix race"', "depends_on:", "  - S-000", "status: todo", nl="\r\n")
        data, body = fm.parse(text)
        self.assertEqual(data, {"id": "S-001", "title": "Auth: Fix race", "depends_on": ["S-000"], "status": "todo"})
        self.assertEqual(body, "body\r\n")
        out = fm.set_fields(text, {"status": "done", "notes": "ok"})
        self.assertNotIn("\n", out.replace("\r\n", ""), "mixed line endings after set_fields")
        self.assertEqual(fm.parse(out)[0]["status"], "done")
        self.assertEqual(fm.parse("﻿" + text)[0]["id"], "S-001")

    def test_escapes_and_types(self):
        data, _ = fm.parse(doc('esc: "say \\"hi\\"\\nbye"', "single: 'it''s'", "flag: true", "n: -3",
                               "nothing: ~", 'num_str: "42"', "desc: |", "  line 1", "  line 2", "z: 1"))
        self.assertEqual(data["esc"], 'say "hi"\nbye')
        self.assertEqual(data["single"], "it's")
        self.assertIs(data["flag"], True)
        self.assertEqual(data["n"], -3)
        self.assertIsNone(data["nothing"])
        self.assertEqual(data["num_str"], "42")
        self.assertEqual(data["desc"], "line 1\nline 2")

    def test_set_fields_round_trip(self):
        text = doc("id: S-001", "status: todo # was todo", "targets:", "  - a.ts", "  - b.ts", "model: opus")
        tricky = {"status": "blocked", "notes": 'Auth: "x" # y\nline2', "targets": ["c.ts", "d, e.ts"],
                  "flag_str": "true", "count": 3}
        data, body = fm.parse(fm.set_fields(text, tricky))
        for k, v in tricky.items():
            self.assertEqual(data[k], v, k)
        self.assertEqual(data["model"], "opus")
        self.assertEqual(body, "body\n")

    def test_malformed_lines_are_not_fatal(self):
        data, _ = fm.parse(doc('title: "unterminated', "ok: yes", "not a key line"))
        self.assertTrue(data["ok"])
        self.assertIn("title", data)


if __name__ == "__main__":
    unittest.main()
