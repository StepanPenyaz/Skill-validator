"""Tests for compute_similarity.py and the recommendation in build_final_report.py.

Run: python -m unittest discover skill-eval/tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_final_report as bfr  # noqa: E402
import compute_similarity as cs  # noqa: E402

PROFILE = {
    "weights": {"fact_recall": 0.6, "content_overlap": 0.25, "structure": 0.15},
    "required_sections": ["Title", "Description", "AC"],
    "count_section": "AC",
    "unit_aliases": {"ms": "ms", "min": "min", "minutes": "min", "s": "s", "seconds": "s"},
}

VERIFIED = """### Title
Add endpoint

### Description
Call `POST /api/v1/x` with `reason` (`CHANGED_MIND`, `OTHER`). Out of scope: mobile.

### AC
1. Given a bad request, Then the response is `400`.
2. p95 response time <= 300 ms.
3. Lock for 15 minutes after 5 attempts (see item 2).
"""


class SimilarityTests(unittest.TestCase):
    def test_identical_text_scores_100(self):
        r = cs.score_case(VERIFIED, VERIFIED, PROFILE)
        self.assertAlmostEqual(r["similarity"], 100.0, places=3)
        self.assertEqual(r["missing"], [])

    def test_missing_fact_lowers_recall(self):
        produced = VERIFIED.replace("`400`", "an error")
        r = cs.score_case(VERIFIED, produced, PROFILE)
        self.assertIn("400", r["missing"])
        self.assertLess(r["fact_recall"], 100.0)

    def test_unit_aliases_match_and_wrong_unit_does_not(self):
        facts = cs.extract_facts("Limit is 15 min.", PROFILE)
        ok, _ = cs.fact_recall(facts, "Locked for 15 minutes.", PROFILE)
        bad, _ = cs.fact_recall(facts, "Locked for 15 seconds.", PROFILE)
        self.assertEqual(ok, 1.0)
        self.assertEqual(bad, 0.0)

    def test_thousands_separator_and_item_references(self):
        self.assertEqual(cs.numeric_facts("100,000 rows, see item 7", PROFILE["unit_aliases"]), {"100000"})

    def test_list_numbers_are_not_facts(self):
        self.assertNotIn("1", cs.numeric_facts("1. Do it", PROFILE["unit_aliases"]))

    def test_snake_case_identifiers_survive_cleaning(self):
        facts = cs.identifier_facts("`CHANGED_MIND`")
        recall, _ = cs.fact_recall({"numbers": set(), "identifiers": facts}, "reason changed_mind", PROFILE)
        self.assertEqual(recall, 1.0)

    def test_structure_penalises_missing_section_and_item_count(self):
        no_ac = "### Title\nx\n### Description\ny\n"
        self.assertLess(cs.structure_score(VERIFIED, no_ac, PROFILE), 0.5)
        self.assertEqual(cs.structure_score(VERIFIED, VERIFIED, PROFILE), 1.0)

    def test_two_pbis_in_one_case_are_counted_together(self):
        two = VERIFIED + "\n### Title\nSecond\n### Description\nz\n### AC\n1. a\n2. b\n"
        # verified has 3 AC items; the split output has 3 + 2 = 5 -> ratio 0.6
        self.assertAlmostEqual(cs.structure_score(VERIFIED, two, PROFILE), (1.0 + 0.6) / 2)

    def test_split_produced_by_case_header(self):
        parts = cs.split_produced("# t\n## a.md\nA text\n## b.md\nB text\n")
        self.assertEqual(set(parts), {"a.md", "b.md"})
        self.assertIn("B text", parts["b.md"])

    def test_empty_overlap_is_zero(self):
        self.assertEqual(cs.f1_overlap("alpha beta", "gamma delta"), 0.0)


def row(model, sim, verdict=None, cost=1.0, time=60, tokens=1000):
    return {"model": model, "similarity": sim, "verdict": verdict, "cost": cost, "time": time, "tokens": tokens}


class RecommendTests(unittest.TestCase):
    def test_cheapest_within_tolerance_wins(self):
        res = bfr.recommend([row("opus", 90, cost=1.0), row("sonnet", 88, cost=0.4), row("haiku", 80, cost=0.1)], 3)
        self.assertEqual(res["recommended"]["model"], "sonnet")

    def test_best_alone_when_others_outside_tolerance(self):
        res = bfr.recommend([row("opus", 95, cost=1.0), row("haiku", 80, cost=0.1)], 3)
        self.assertEqual(res["recommended"]["model"], "opus")

    def test_major_gaps_excluded_even_if_best(self):
        res = bfr.recommend([row("opus", 95, "major gaps"), row("sonnet", 85, "minor gaps")], 3)
        self.assertEqual(res["recommended"]["model"], "sonnet")
        self.assertEqual(res["excluded"], [("opus", "verdict: major gaps")])

    def test_missing_cost_or_similarity_excluded(self):
        res = bfr.recommend([row("a", None), row("b", 90, cost=None), row("c", 70)], 3)
        self.assertEqual(res["recommended"]["model"], "c")
        self.assertEqual(len(res["excluded"]), 2)

    def test_cost_tie_broken_by_time_then_similarity(self):
        res = bfr.recommend([row("a", 90, cost=1, time=120), row("b", 89, cost=1, time=60)], 3)
        self.assertEqual(res["recommended"]["model"], "b")

    def test_nothing_usable_gives_no_recommendation(self):
        res = bfr.recommend([row("a", None)], 3)
        self.assertIsNone(res["recommended"])

    def test_verdict_line_parsing(self):
        m = bfr.VERDICT_LINE.search("| a |\n\nVerdict: Minor gaps - misses 401\n")
        self.assertEqual((m.group(1).lower(), m.group(2)), ("minor gaps", "misses 401"))


if __name__ == "__main__":
    unittest.main()
