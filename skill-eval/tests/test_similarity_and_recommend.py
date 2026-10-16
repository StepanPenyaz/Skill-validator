"""Tests for compute_similarity.py, the recommendation and reports of build_final_report.py, and run_skill.py.

Run: python -m unittest discover skill-eval/tests
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import build_final_report as bfr  # noqa: E402
import compute_similarity as cs  # noqa: E402
import run_skill as rs  # noqa: E402
import profiles  # noqa: E402
from profiles import document as doc  # noqa: E402

PROFILE = {
    "weights": {"fact_recall": 0.6, "content_overlap": 0.25, "structure": 0.15},
    "required_sections": ["Title", "Description", "AC"],
    "count_section": "AC",
    "unit_aliases": {"ms": "ms", "min": "min", "minutes": "min", "s": "s", "seconds": "s"},
}
STABILITY = {"max_case_spread_points": 10, "min_valid_runs": 2, "low_case_points": 60}

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
        r = doc.score_case(VERIFIED, VERIFIED, PROFILE)
        self.assertAlmostEqual(r["similarity"], 100.0, places=3)
        self.assertEqual(r["missing"], [])

    def test_no_output_scores_zero_and_is_marked(self):
        r = doc.score_case(VERIFIED, None, PROFILE)
        self.assertEqual(r["similarity"], 0.0)
        self.assertTrue(r["no_output"])

    def test_missing_fact_lowers_recall(self):
        r = doc.score_case(VERIFIED, VERIFIED.replace("`400`", "an error"), PROFILE)
        self.assertIn("400", r["missing"])
        self.assertLess(r["fact_recall"], 100.0)

    def test_unit_aliases_match_and_wrong_unit_does_not(self):
        facts = doc.extract_facts("Limit is 15 min.", PROFILE)
        self.assertEqual(doc.fact_recall(facts, "Locked for 15 minutes.", PROFILE)[0], 1.0)
        self.assertEqual(doc.fact_recall(facts, "Locked for 15 seconds.", PROFILE)[0], 0.0)

    def test_thousands_separator_and_item_references(self):
        self.assertEqual(doc.numeric_facts("100,000 rows, see item 7", PROFILE["unit_aliases"]), {"100000"})

    def test_snake_case_identifiers_survive_cleaning(self):
        facts = doc.identifier_facts("`CHANGED_MIND`")
        self.assertEqual(doc.fact_recall({"numbers": set(), "identifiers": facts}, "reason changed_mind", PROFILE)[0], 1.0)

    def test_structure(self):
        self.assertLess(doc.structure_score(VERIFIED, "### Title\nx\n### Description\ny\n", PROFILE), 0.5)
        self.assertEqual(doc.structure_score(VERIFIED, VERIFIED, PROFILE), 1.0)
        two = VERIFIED + "\n### Title\nSecond\n### Description\nz\n### AC\n1. a\n2. b\n"
        self.assertAlmostEqual(doc.structure_score(VERIFIED, two, PROFILE), (1.0 + 0.6) / 2)


def results(*scores_by_run, missing_in=()):
    """{run: {case: result}} for cases c1, c2 with the given similarities per run."""
    out = {}
    for r, (a, b) in enumerate(scores_by_run, 1):
        out[r] = {"c1": {"similarity": a, "fact_recall": a, "content_overlap": a, "structure": a, "no_output": (r, "c1") in missing_in},
                  "c2": {"similarity": b, "fact_recall": b, "content_overlap": b, "structure": b, "no_output": (r, "c2") in missing_in}}
    return out


class StabilityTests(unittest.TestCase):
    cases = ["c1", "c2"]

    def test_stable_when_the_same_case_barely_changes_between_runs(self):
        # c1 is always high and c2 always low: different cases differ a lot, repeats do not
        a = cs.analyze_model(results((90, 50), (92, 52), (91, 51)), self.cases, STABILITY)
        self.assertEqual(a["status"], "stable")
        self.assertAlmostEqual(a["score"], 71.0)

    def test_unstable_when_repeats_of_one_case_differ(self):
        a = cs.analyze_model(results((90, 50), (60, 20), (75, 35)), self.cases, STABILITY)
        self.assertEqual(a["status"], "unstable")
        self.assertAlmostEqual(a["mean_case_spread"], 30.0)

    def test_incomplete_run_is_not_in_the_score_but_in_all_runs(self):
        a = cs.analyze_model(results((90, 90), (0, 0), (80, 80), missing_in={(2, "c1"), (2, "c2")}), self.cases, STABILITY)
        self.assertEqual(a["valid_runs"], 2)
        self.assertAlmostEqual(a["score"], 85.0)
        self.assertAlmostEqual(a["all_runs_score"], (90 + 0 + 80) / 3)

    def test_too_few_complete_runs_is_insufficient_not_unstable(self):
        a = cs.analyze_model(results((90, 90), (0, 0), (0, 0), missing_in={(2, "c1"), (3, "c2")}), self.cases, STABILITY)
        self.assertEqual(a["status"], "insufficient")

    def test_single_run_model(self):
        a = cs.analyze_model(results((90, 80)), self.cases, STABILITY)
        self.assertEqual(a["status"], "single run")
        self.assertIsNone(a["run_spread"])

    def test_median_run(self):
        a = cs.analyze_model(results((50, 50), (90, 90), (70, 70)), self.cases, {**STABILITY, "max_case_spread_points": 100})
        self.assertEqual(a["median_run"], 3)

    def test_skill_flag_needs_two_unstable_models(self):
        un = {"status": "unstable", "runs": [], "valid_runs": 3}
        ok = {"status": "stable", "runs": [], "valid_runs": 3}
        self.assertTrue(any("Skill flag" in f for f in cs.skill_flags({"a": un, "b": dict(un), "c": ok}, [], STABILITY)))
        one = cs.skill_flags({"a": un, "b": ok}, [], STABILITY)
        self.assertFalse(any("Skill flag" in f for f in one))
        self.assertTrue(any("Model note" in f for f in one))

    def test_low_case_flag(self):
        runs = results((50, 90), (52, 91))
        a = cs.analyze_model(runs, self.cases, STABILITY)
        self.assertTrue(any("c1" in f and "verified output" in f for f in cs.skill_flags({"m": a}, self.cases, STABILITY)))


def row(model, sim, verdict=None, cost=1.0, time=60, tokens=1000, status="stable", spread=None):
    return {"model": model, "similarity": sim, "verdict": verdict, "cost": cost, "time": time, "tokens": tokens,
            "status": status, "spread": spread}


class RecommendTests(unittest.TestCase):
    def test_cheapest_within_tolerance_wins(self):
        res = bfr.recommend([row("opus", 90, cost=1.0), row("sonnet", 88, cost=0.4), row("haiku", 80, cost=0.1)], 3)
        self.assertEqual(res["recommended"]["model"], "sonnet")

    def test_tolerance_grows_with_run_spread_of_the_remaining_models(self):
        rows = [row("opus", 90, cost=1.0, spread=8), row("haiku", 83, cost=0.1, spread=2)]
        self.assertEqual(bfr.recommend(rows, 3)["recommended"]["model"], "haiku")
        self.assertEqual(bfr.recommend(rows, 3)["tolerance"], 8)
        rows[0]["spread"] = 1
        self.assertEqual(bfr.recommend(rows, 3)["recommended"]["model"], "opus")

    def test_major_gaps_excluded_even_if_best(self):
        res = bfr.recommend([row("opus", 95, "major gaps"), row("sonnet", 85, "minor gaps")], 3)
        self.assertEqual(res["recommended"]["model"], "sonnet")
        self.assertEqual(res["excluded"], [("opus", "verdict: major gaps")])

    def test_disputed_verdict_keeps_the_model(self):
        self.assertEqual(bfr.recommend([row("opus", 95, "disputed"), row("sonnet", 80)], 3)["recommended"]["model"], "opus")

    def test_unstable_and_insufficient_models_are_not_recommended(self):
        res = bfr.recommend([row("a", 95, status="unstable"), row("b", 94, status="insufficient"), row("c", 70)], 3)
        self.assertEqual(res["recommended"]["model"], "c")
        self.assertEqual(len(res["excluded"]), 2)

    def test_everything_unstable_gives_no_recommendation(self):
        self.assertIsNone(bfr.recommend([row("a", 95, status="unstable"), row("b", 90, status="unstable")], 3)["recommended"])

    def test_missing_cost_or_similarity_excluded(self):
        res = bfr.recommend([row("a", None), row("b", 90, cost=None), row("c", 70)], 3)
        self.assertEqual(res["recommended"]["model"], "c")

    def test_cost_tie_broken_by_time(self):
        res = bfr.recommend([row("a", 90, cost=1, time=120), row("b", 89, cost=1, time=60)], 3)
        self.assertEqual(res["recommended"]["model"], "b")


class VerdictTests(unittest.TestCase):
    def test_verdict_line_parsing(self):
        m = bfr.VERDICT_LINE.search("| a |\n\nVerdict: Minor gaps - misses 401\n")
        self.assertEqual((m.group(1).lower(), m.group(2)), ("minor gaps", "misses 401"))

    def test_two_judges(self):
        self.assertEqual(bfr.combine_verdicts([("major gaps", "x"), ("major gaps", "y")])[0], "major gaps")
        self.assertEqual(bfr.combine_verdicts([("major gaps", "x"), ("minor gaps", "y")])[0], "disputed")
        self.assertEqual(bfr.combine_verdicts([("equivalent", "x"), ("minor gaps", "y")])[0], "minor gaps")
        self.assertEqual(bfr.combine_verdicts([("minor gaps", "x")]), ("minor gaps", "x"))
        self.assertIsNone(bfr.combine_verdicts([]))


STRUCTURE = """# Static Check Report: demo

1 blocker(s), 1 warning(s), 0 info-level suggestion(s).

## Metadata

| What's Wrong | Severity | Suggested Fix |
|---|---|---|
| Frontmatter 'name' is missing. | Blocker | Add a name \\| kebab-case. |
| Description is short. | Warning | Expand it. |
"""


def make_skill(root, structure=None, generated=False):
    root = Path(root)
    (root / "step_reports").mkdir(parents=True)
    (root / "SKILL.md").write_text("---\nname: demo\ndescription: Does a thing. Use when asked.\nmetadata:\n  version: \"1.0.0\"\n---\n\n# Demo\n",
                                   encoding="utf-8")
    if structure:
        (root / "step_reports" / "01_structure.md").write_text(structure, encoding="utf-8")
    if generated:
        (root / "evals").mkdir()
        (root / "evals" / "GENERATED.md").write_text("generated", encoding="utf-8")
    return root


class ReportTests(unittest.TestCase):
    def test_blocker_rows_only(self):
        self.assertEqual(bfr.blocker_rows(STRUCTURE), [("Frontmatter 'name' is missing.", "Add a name | kebab-case.")])

    def test_stopped_run_gives_short_report_with_blocking_section_only(self):
        with tempfile.TemporaryDirectory() as d:
            skill = make_skill(Path(d) / "demo", STRUCTURE)
            bfr.sys.argv = ["x", str(skill)]
            bfr.main()
            short = (skill / "final_report.md").read_text(encoding="utf-8")
            self.assertEqual([l for l in short.splitlines() if l.startswith("## ")],
                             ["## 1. Summary", "## 2. Skill name", "## 3. Skill description", "## 4. Model recommendation",
                              "## 5. Blocking structure findings"])
            self.assertIn("stopped at the structure check", short)
            self.assertIn("Frontmatter 'name' is missing.", short)
            self.assertNotIn("Expand it", short)  # warnings are not in the short report
            self.assertIn("Expand it", (skill / "detailed_final_report.md").read_text(encoding="utf-8"))

    def test_short_report_without_blockers_has_four_sections_and_generated_note(self):
        with tempfile.TemporaryDirectory() as d:
            skill = make_skill(Path(d) / "demo", STRUCTURE.replace("1 blocker(s)", "0 blocker(s)").replace("Blocker", "Info"), generated=True)
            bfr.sys.argv = ["x", str(skill)]
            bfr.main()
            short = (skill / "final_report.md").read_text(encoding="utf-8")
            self.assertEqual(len([l for l in short.splitlines() if l.startswith("## ")]), 4)
            self.assertIn("generated by a subagent", short)

    def test_baseline_reads_the_detailed_report(self):
        with tempfile.TemporaryDirectory() as d:
            v1 = make_skill(Path(d) / "v1", STRUCTURE)
            bfr.sys.argv = ["x", str(v1)]
            bfr.main()
            v2 = make_skill(Path(d) / "v2", STRUCTURE)
            bfr.sys.argv = ["x", str(v2), "--baseline", str(v1)]
            bfr.main()
            self.assertTrue((v2 / "detailed_final_report.md").is_file())


# ---------- run_skill.py ----------

FAKE = [sys.executable, str(HERE / "fake_claude.py")]
RUNNER = {"timeout_seconds": 30, "max_budget_usd": 1.0, "allowed_tools": ["Skill", "Read"]}


def make_runnable_skill(root, cases=("a.md", "b.md")):
    root = Path(root)
    (root / "evals" / "inputs").mkdir(parents=True)
    (root / "evals" / "verified-outputs").mkdir()
    (root / "SKILL.md").write_text("---\nname: demo\ndescription: Does a thing. Use when asked.\nmetadata:\n  version: \"1.0.0\"\n---\n# Demo\n",
                                   encoding="utf-8")
    for c in cases:
        (root / "evals" / "inputs" / c).write_text(f"input {c}", encoding="utf-8")
        (root / "evals" / "verified-outputs" / c).write_text(f"verified {c}", encoding="utf-8")
    return root


class RunnerTests(unittest.TestCase):
    def test_parse_stream_and_summary(self):
        lines = "\n".join(json.dumps(e) for e in [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Skill"}]}},
            {"type": "result", "subtype": "success", "is_error": False, "result": "done",
             "usage": {"input_tokens": 1, "output_tokens": 2, "cache_read_input_tokens": 3, "cache_creation_input_tokens": 4},
             "total_cost_usd": 0.5, "duration_ms": 10, "num_turns": 2}]) + "\nnot json"
        s = rs.summarize_case(lines, 0, "haiku", 1, "a.md")
        self.assertEqual((s["status"], s["tokens"]["total"], s["cost_usd"], s["skill_loaded"]), ("ok", 10, 0.5, True))

    def test_failure_kinds(self):
        self.assertIn("no result", rs.summarize_case("", 1, "m", 1, "a")["reason"])
        err = json.dumps({"type": "result", "subtype": "success", "is_error": True, "result": "Not logged in"})
        self.assertEqual(rs.summarize_case(err, 1, "m", 1, "a")["reason"], "Not logged in")
        empty = json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "  "})
        self.assertEqual(rs.summarize_case(empty, 0, "m", 1, "a")["reason"], "empty output")
        budget = json.dumps({"type": "result", "subtype": "error_max_budget_usd", "is_error": False, "result": "x"})
        self.assertEqual(rs.summarize_case(budget, 0, "m", 1, "a")["status"], "failed")
        self.assertIn("timeout", rs.summarize_case("", None, "m", 1, "a", timed_out=5)["reason"])

    def test_run_case_saves_files_and_hides_evals(self):
        with tempfile.TemporaryDirectory() as d:
            skill = make_runnable_skill(Path(d) / "demo")
            out = skill / "evals" / "demo_1.0.0_outputs"
            s = rs.run_case(("haiku", 1, skill / "evals" / "inputs" / "a.md"), FAKE, skill, out, RUNNER)
            self.assertEqual(s["status"], "ok", s)
            produced, meta, log = rs.case_paths(out, "haiku", 1, "a.md")
            self.assertEqual(produced.read_text(encoding="utf-8"), "haiku: input a.md")
            self.assertEqual(json.loads(meta.read_text(encoding="utf-8"))["tokens"]["total"], 1160)
            self.assertTrue(log.is_file())

    def test_failed_case_is_recorded_and_has_no_output_file(self):
        with tempfile.TemporaryDirectory() as d:
            skill = make_runnable_skill(Path(d) / "demo")
            out = skill / "evals" / "demo_1.0.0_outputs"
            os.environ["FAKE_FAIL_CASE"] = "b.md"
            try:
                s = rs.run_case(("haiku", 1, skill / "evals" / "inputs" / "b.md"), FAKE, skill, out, RUNNER)
            finally:
                del os.environ["FAKE_FAIL_CASE"]
            self.assertEqual(s["status"], "failed")
            produced, meta, _ = rs.case_paths(out, "haiku", 1, "b.md")
            self.assertFalse(produced.exists())
            self.assertEqual(json.loads(meta.read_text(encoding="utf-8"))["status"], "failed")

    def test_timeout_is_a_failed_case(self):
        with tempfile.TemporaryDirectory() as d:
            skill = make_runnable_skill(Path(d) / "demo")
            out = skill / "evals" / "demo_1.0.0_outputs"
            os.environ["FAKE_MODE"] = "hang"
            try:
                s = rs.run_case(("haiku", 1, skill / "evals" / "inputs" / "a.md"), FAKE, skill, out, {**RUNNER, "timeout_seconds": 1})
            finally:
                del os.environ["FAKE_MODE"]
            self.assertEqual(s["status"], "failed")
            self.assertIn("timeout", s["reason"])

    def test_reports_and_similarity_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            skill = make_runnable_skill(Path(d) / "demo")
            out = skill / "evals" / "demo_1.0.0_outputs"
            cases = [skill / "evals" / "inputs" / c for c in ("a.md", "b.md")]
            os.environ["FAKE_FAIL_CASE"] = "b.md"
            try:
                for run in (1, 2):
                    for c in cases:
                        rs.run_case(("haiku", run, c), FAKE, skill, out, RUNNER)
            finally:
                del os.environ["FAKE_FAIL_CASE"]
            for c in cases:  # run 3 is complete
                rs.run_case(("haiku", 3, c), FAKE, skill, out, RUNNER)
            rs.write_reports(skill, ["haiku"], ["a.md", "b.md"])
            report = (out / "run_on_haiku_report.md").read_text(encoding="utf-8")
            self.assertIn("- Model name: haiku", report)
            self.assertIn("- Runs: 3", report)
            self.assertIn("- Complete runs: 1", report)
            runs = bfr.read_runs(skill, bfr.skill_meta(skill))
            self.assertEqual(runs["haiku"]["tokens"], 2320)
            self.assertAlmostEqual(runs["haiku"]["cost"], 0.34, places=3)  # runs cost 0.25 + 0.01 (failed case), 0.26, 0.5
            produced = cs.read_runs(out, ["a.md", "b.md"])
            self.assertIsNone(produced["haiku"][1]["b.md"])
            self.assertIsNotNone(produced["haiku"][3]["b.md"])


class ProfileContractTests(unittest.TestCase):
    """The self-test every implemented profile must pass (see references/profiles.md)."""

    @staticmethod
    def implemented():
        cfg = bfr.load_config()["profiles"]
        return [name for name, section in cfg.items() if section.get("status") == "implemented"]

    def test_there_is_a_default_profile_and_it_is_implemented(self):
        self.assertIn(bfr.load_config()["default_profile"], self.implemented())

    def test_planned_profiles_stop_with_a_message(self):
        planned = [n for n, s in bfr.load_config()["profiles"].items() if s.get("status") != "implemented"]
        for name in planned:
            with self.assertRaises(SystemExit):
                profiles.get_profile(name)

    def test_unknown_profile_stops(self):
        with self.assertRaises(SystemExit):
            profiles.get_profile("no-such-profile")

    def test_contract_of_every_implemented_profile(self):
        for name in self.implemented():
            with self.subTest(profile=name):
                prof = profiles.get_profile(name)
                self.assertTrue(prof.verified_glob)
                opts = prof.run_options()
                self.assertIn("{input_file}", opts["prompt"])
                self.assertTrue(opts["allowed_tools"])
                self.assertEqual(prof.check_applicable("."), (True, ""))
                self.assertTrue(prof.components)
                keys = [k for k, _ in prof.components]
                verified = VERIFIED
                same = prof.score(verified, verified)
                self.assertAlmostEqual(same["similarity"], 100.0, places=3)
                none = prof.score(verified, None)
                self.assertEqual(none["similarity"], 0.0)
                self.assertTrue(none["no_output"])
                broken = prof.score(verified, "unrelated words only")
                self.assertLess(broken["similarity"], same["similarity"])
                for k in keys:
                    self.assertIn(k, same)

    def test_collect_default_is_the_reply(self):
        self.assertEqual(profiles.get_profile().collect("reply", "."), "reply")

    def test_document_profile_keeps_its_formula(self):
        prof = profiles.get_profile("document")
        sentence, bullets = prof.report_intro()
        self.assertIn("0.60 x fact recall + 0.25 x content overlap + 0.15 x structure", sentence)
        self.assertEqual(len(bullets), 3)


class StaticGateTests(unittest.TestCase):
    def run_gate(self, skill):
        import subprocess
        return subprocess.run([sys.executable, str(HERE.parent / "scripts" / "generate_static_report.py"), str(skill),
                               "--fail-on-blocker", "--out", str(Path(skill).parent / "r.md")],
                              capture_output=True, text=True).returncode

    def test_exit_code_2_only_with_blockers(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / 'bad'
            bad.mkdir()
            (bad / 'SKILL.md').write_text('# no frontmatter'+chr(10), encoding='utf-8')
            self.assertEqual(self.run_gate(bad), 2)
            good = Path(d) / 'good'
            good.mkdir()
            text = chr(10).join(['---', 'name: good', 'description: Does a useful thing for the user. Use when asked to do the thing.',
                                 'metadata:', '  version: '+chr(34)+'1.0.0'+chr(34), '---', '# Good', ''])
            (good / 'SKILL.md').write_text(text, encoding='utf-8')
            self.assertEqual(self.run_gate(good), 0)


if __name__ == "__main__":
    unittest.main()
