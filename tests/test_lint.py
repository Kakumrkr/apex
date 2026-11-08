import json
import os
import unittest

from helpers import SCORECARD, DIMS, ProjectCase, packet, roadmap
from apex_core import lint


def codes(report):
    return {e["code"] for e in report.errors}


class GoodProject(ProjectCase):
    def test_valid_fixture_passes(self):
        r = lint.run(self.p, require_roadmap=True)
        self.assertEqual(r.errors, [], r.text())


class Scorecard(ProjectCase):
    def test_score_must_match_rubric(self):
        self.write(".apex/roadmap.md", roadmap(dict(SCORECARD, overall=8.5)))
        self.assertIn("score-math", codes(lint.run(self.p)))

    def test_broken_build_caps_score(self):
        card = dict(SCORECARD, health={"status": "fail"})  # weighted 6.3 > cap 4.5
        self.write(".apex/roadmap.md", roadmap(card))
        self.assertIn("score-cap", codes(lint.run(self.p)))
        low = {k: 4.0 for k in DIMS}
        self.write(".apex/roadmap.md", roadmap(dict(card, dimensions=low, overall=4.0)))
        self.assertNotIn("score-cap", codes(lint.run(self.p)))

    def test_dimension_range_and_unknown(self):
        self.write(".apex/roadmap.md", roadmap(dict(SCORECARD, dimensions=dict(DIMS, testing=11, vibes=9))))
        msgs = " ".join(e["message"] for e in lint.run(self.p).errors)
        self.assertIn("testing", msgs)
        self.assertIn("vibes", msgs)

    def test_missing_scorecard_block(self):
        self.write(".apex/roadmap.md", roadmap().replace("<!-- apex:scorecard", "<!-- nope"))
        self.assertIn("scorecard", codes(lint.run(self.p)))

    def test_big_delta_needs_justification(self):
        self.write(".apex/state.json", json.dumps({"score": 4.0, "tier": 1}))
        self.assertIn("big-delta", codes(lint.run(self.p)))
        self.write(".apex/roadmap.md", roadmap(dict(SCORECARD, delta_justification=
                   "Auth flow rebuilt with tests (src/auth/*), build now green, 14 new tests.")))
        self.assertNotIn("big-delta", codes(lint.run(self.p)))

    def test_health_evidence_mismatch(self):
        self.write(".apex/.health.json", json.dumps({"sha": None, "status": "fail", "results": []}))
        self.assertIn("health-mismatch", codes(lint.run(self.p)))

    def test_missing_section(self):
        self.write(".apex/roadmap.md", roadmap().replace("## First 60 Seconds", "## Onboarding"))
        self.assertIn("roadmap", codes(lint.run(self.p)))


class Provenance(ProjectCase):
    def test_unobserved_verified_url_fails(self):
        rows = ["| Sync | Acme | Beats | made up | https://acme.example.com/fabricated | verified | 2026-11-01 |"]
        self.write(".apex/roadmap.md", roadmap(parity_rows=rows))
        self.assertIn("provenance", codes(lint.run(self.p)))

    def test_unverified_needs_no_url(self):
        rows = ["| Sync | Acme | Beats | from memory | - | unverified | 2026-11-01 |"]
        self.write(".apex/roadmap.md", roadmap(parity_rows=rows))
        self.assertNotIn("provenance", codes(lint.run(self.p)))

    def test_verified_without_url_fails(self):
        rows = ["| Sync | Acme | Beats | x | - | verified | 2026-11-01 |"]
        self.write(".apex/roadmap.md", roadmap(parity_rows=rows))
        self.assertIn("provenance", codes(lint.run(self.p)))

    def test_url_normalization(self):
        rows = ["| Q | Acme | Matches | x | https://www.ACME.example.com/features/?utm_source=x | verified | d |"]
        self.write(".apex/roadmap.md", roadmap(parity_rows=rows))
        self.assertNotIn("provenance", codes(lint.run(self.p)))

    def test_bad_verdict(self):
        rows = ["| Q | Acme | Better | x | - | unverified | d |"]
        self.write(".apex/roadmap.md", roadmap(parity_rows=rows))
        self.assertIn("parity", codes(lint.run(self.p)))


class CommittedResearch(ProjectCase):
    use_git = True

    def test_committed_competitors_md_counts_as_observed(self):
        self.write(".apex/research/competitors.md", "Source: https://boardly.example.com/pricing\n")
        rows = ["| Pricing | Boardly | Matches | x | https://boardly.example.com/pricing | verified | d |"]
        self.write(".apex/roadmap.md", roadmap(parity_rows=rows))
        self.assertIn("provenance", codes(lint.run(self.p)), "uncommitted research must not count")
        from helpers import git
        git(self.tmp, "add", "-A")
        git(self.tmp, "commit", "-q", "-m", "research")
        self.assertNotIn("provenance", codes(lint.run(self.p)))


class Decisions(ProjectCase):
    def test_wont_fix_slug_collision(self):
        opp = ["| `sso-login` | SSO | 3 | 2 | 1.5 | 3 | - |"]
        self.write(".apex/roadmap.md", roadmap(opp_rows=opp))
        self.assertIn("wont-fix", codes(lint.run(self.p)))

    def test_similar_title_different_slug_is_fine(self):
        opp = ["| `login-rate-limiting` | Login rate limiting (not SSO) | 3 | 1 | 3 | 2 | - |"]
        self.write(".apex/roadmap.md", roadmap(opp_rows=opp))
        self.assertEqual(codes(lint.run(self.p)) & {"wont-fix", "deferred"}, set())

    def test_deferred_requires_ack(self):
        opp = ["| `offline-mode` | Offline | 4 | 2 | 2 | 3 | - |"]
        self.write(".apex/roadmap.md", roadmap(opp_rows=opp))
        self.assertIn("deferred", codes(lint.run(self.p)))
        opp = ["| `offline-mode` | Offline | 4 | 2 | 2 | 3 | DF-001 |"]
        self.write(".apex/roadmap.md", roadmap(opp_rows=opp))
        self.assertNotIn("deferred", codes(lint.run(self.p)))

    def test_unknown_decision_reference(self):
        opp = ["| `undo` | Undo | 4 | 1 | 4 | 3 | WF-099 |"]
        self.write(".apex/roadmap.md", roadmap(opp_rows=opp))
        self.assertIn("decision-ref", codes(lint.run(self.p)))


class Packets(ProjectCase):
    def test_too_many_targets(self):
        self.write(".apex/sessions/S-001-add-error-boundaries.md",
                   packet(targets=[f"src/f{i}.ts" for i in range(6)]))
        self.assertIn("packet", codes(lint.run(self.p)))

    def test_parallel_overlap(self):
        self.write(".apex/sessions/S-003-other.md",
                   packet("S-003", "other", targets=["src/app/dashboard/error.tsx"], opportunity="cmd-k-palette"))
        self.assertIn("parallel", codes(lint.run(self.p)))

    def test_missing_dependency_and_cycle(self):
        self.write(".apex/sessions/S-001-add-error-boundaries.md",
                   packet(parallel="depends", depends=["S-002"]))
        msgs = " ".join(e["message"] for e in lint.run(self.p).errors)
        self.assertIn("cycle", msgs)
        self.write(".apex/sessions/S-001-add-error-boundaries.md", packet(parallel="depends", depends=["S-009"]))
        self.assertIn("does not exist", " ".join(e["message"] for e in lint.run(self.p).errors))

    def test_filename_and_sections(self):
        self.write(".apex/sessions/S-003-wrong-name.md",
                   packet("S-003", "other-slug", opportunity="cmd-k-palette",
                          targets=["src/x.ts"]).replace("## Risk & Rollback", "## Risks"))
        msgs = " ".join(e["message"] for e in lint.run(self.p).errors)
        self.assertIn("filename", msgs)
        self.assertIn("Risk & Rollback", msgs)

    def test_estimate_bounds(self):
        self.write(".apex/sessions/S-001-add-error-boundaries.md", packet(estimate=6))
        self.assertIn("estimate_hours", " ".join(e["message"] for e in lint.run(self.p).errors))


class Immutability(ProjectCase):
    use_git = True

    def build(self):
        super().build()
        self.write(".apex/sessions/S-001-add-error-boundaries.md", packet(status="done"))

    def test_done_packets_cannot_change(self):
        path = os.path.join(self.tmp, ".apex/sessions/S-001-add-error-boundaries.md")
        self.assertNotIn("immutable", codes(lint.run(self.p)))
        with open(path, "a") as fh:
            fh.write("\nsneaky edit\n")
        self.assertIn("immutable", codes(lint.run(self.p)))
        os.remove(path)
        self.assertIn("immutable", codes(lint.run(self.p)))


class Secrets(ProjectCase):
    def test_secret_in_roadmap(self):
        self.write(".apex/roadmap.md", roadmap(extra="Found key AKIAIOSFODNN7EXAMPLF in config.ts"))
        self.assertIn("secret", codes(lint.run(self.p)))

    def test_placeholders_ignored(self):
        self.write(".apex/roadmap.md", roadmap(extra='Use API_KEY="your-api-key-here" in .env.example'))
        self.assertNotIn("secret", codes(lint.run(self.p)))


if __name__ == "__main__":
    unittest.main()
