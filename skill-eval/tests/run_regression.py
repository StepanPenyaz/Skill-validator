#!/usr/bin/env python3
"""
run_regression.py — skill-eval's own regression suite.

`skill-eval` absorbed `skill-review`'s static-review layer (structural_check.py,
generate_static_report.py, reconcile_reviews.py, diff_reviews.py, and their
fixtures) into this skill — see CHANGELOG.md's merge entry. This suite now
covers both halves in one place:

- The deterministic static-review checks: structural_check.py against every
  fixture under tests/fixtures/ (bad-skill, good-skill,
  clean-skill-with-tricky-patterns), reconcile_reviews.py against the
  consistency-runs fixture, diff_reviews.py against both the deterministic
  (diff-old-skill/diff-new-skill) and qualitative (version-diff) fixtures.
- models_config.yaml loading and shape.
- render_report.py's table rendering from a fixed, hand-written sample input
  (and the zero-runs edge case).
- Self-check: skill-eval's own SKILL.md passes its own gate mode.
- Packaging: skill-eval still packages cleanly.

Explicitly out of scope, same reasoning as before: anything requiring a live
model call — task execution (Workflow step 2), judgment-writing (step 3), or
the qualitative full review pass. Those aren't scriptable this way.

Plain assertions over subprocess calls to real CLI entrypoints, no test
framework, stdlib only (PyYAML is already a stated dependency).

Usage:
    python3 tests/run_regression.py

Exits 0 if every check passes; 1 (after printing every failure, not just
the first) otherwise.
"""

import json
import subprocess
import sys
from pathlib import Path

# On Windows, stdout otherwise defaults to the console's codepage — same
# fix as scripts/render_report.py and the other scripts.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent  # skill-eval/
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"

_failures = []
_checks_run = 0


def run(*args):
    """Runs `python3 <args>` exactly as a user would, returning (stdout, returncode, stderr)."""
    proc = subprocess.run(
        [sys.executable, *(str(a) for a in args)],
        capture_output=True, text=True,
    )
    return proc.stdout, proc.returncode, proc.stderr


def run_json(*args):
    stdout, returncode, stderr = run(*args)
    if returncode != 0:
        raise AssertionError(
            f"{' '.join(str(a) for a in args)} exited {returncode}: {stderr.strip() or stdout.strip()}"
        )
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"{' '.join(str(a) for a in args)} did not print valid JSON ({e}): {stdout[:300]!r}"
        )


def check(name):
    """Decorator: registers and immediately runs `fn` as one named regression
    check, catching AssertionError so one failure doesn't stop the rest."""
    def decorator(fn):
        global _checks_run
        _checks_run += 1
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            print(f"FAIL  {name}: {e}")
            _failures.append(name)
        return fn
    return decorator


def assert_eq(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def assert_true(cond, label):
    if not cond:
        raise AssertionError(f"{label}: expected a truthy value, got {cond!r}")


def assert_in(needle, haystack, label):
    if needle not in haystack:
        raise AssertionError(f"{label}: expected {needle!r} to appear in output")


def assert_check_ids(findings, expected_ids, label):
    """Asserts `findings` contains at least one finding for every check_id in
    expected_ids — set-based (a check firing more than once is still one entry
    in this set), so this verifies each SPECIFIC documented issue was actually
    caught, not just that the raw finding count didn't change."""
    actual_ids = {f["check_id"] for f in findings}
    missing = sorted(set(expected_ids) - actual_ids)
    if missing:
        raise AssertionError(f"{label}: missing expected check_id(s) {missing}; got {sorted(actual_ids)}")


# ============================================================
# Static-review layer (absorbed from skill-review)
# ============================================================

# --- good-skill: should be entirely clean, including the two soft (Info) checks ---
@check("good-skill: zero compliance errors and zero structural warnings")
def _():
    result = run_json(SCRIPTS / "structural_check.py", FIXTURES / "good-skill")
    assert_eq(result["compliance_errors"], [], "compliance_errors")
    assert_eq(result["structural_warnings"], [], "structural_warnings")
    assert_eq(result["findings"], [], "findings")


@check("good-skill: security scan skipped (no shell/network tool declared or referenced)")
def _():
    result = run_json(SCRIPTS / "structural_check.py", FIXTURES / "good-skill")
    assert_eq(result["metrics"]["security_scan"]["skipped"], True, "security_scan.skipped")


# --- bad-skill: every issue documented in its own SKILL.md intro must actually fire ---
BAD_SKILL_EXPECTED_CHECK_IDS = {
    "name_not_kebab_case",
    "name_folder_mismatch",
    "description_too_short",
    "description_no_trigger_cue",
    "metadata_version_missing",
    "portability_path",
    "orphaned_resource_file",
    "must_never_line",
    "tool_declared_unreferenced",
    "tool_referenced_undeclared",
    "hardcoded_secret",
    "dangerous_shell_pattern",
    "undeclared_external_host",
    "prompt_injection_phrase",
    "prohibited_action_phrase",
}


@check("bad-skill: every issue documented in SKILL.md's own intro fires as a finding")
def _():
    result = run_json(SCRIPTS / "structural_check.py", FIXTURES / "bad-skill")
    assert_check_ids(result["findings"], BAD_SKILL_EXPECTED_CHECK_IDS, "bad-skill findings")


@check("bad-skill: hardcoded secret is a Blocker (compliance_errors), not just a Warning")
def _():
    result = run_json(SCRIPTS / "structural_check.py", FIXTURES / "bad-skill")
    secret_findings = [f for f in result["findings"] if f["check_id"] == "hardcoded_secret"]
    assert len(secret_findings) >= 1, "expected at least one hardcoded_secret finding"
    assert_eq(secret_findings[0]["severity"], "Blocker", "hardcoded_secret severity")
    assert len(result["compliance_errors"]) >= 1, "expected compliance_errors to be non-empty"


@check("bad-skill: security scan NOT skipped (declares WebSearch, references Bash)")
def _():
    result = run_json(SCRIPTS / "structural_check.py", FIXTURES / "bad-skill")
    assert_eq(result["metrics"]["security_scan"]["skipped"], False, "security_scan.skipped")


# --- clean-skill-with-tricky-patterns: precision test, must stay silent ---
@check("clean-skill-with-tricky-patterns: zero findings despite surface-similar-to-bad patterns")
def _():
    result = run_json(SCRIPTS / "structural_check.py", FIXTURES / "clean-skill-with-tricky-patterns")
    assert_eq(result["compliance_errors"], [], "compliance_errors")
    assert_eq(result["structural_warnings"], [], "structural_warnings")
    assert_eq(result["findings"], [], "findings")


@check("clean-skill-with-tricky-patterns: security scan NOT skipped (declares+references Bash)")
def _():
    result = run_json(SCRIPTS / "structural_check.py", FIXTURES / "clean-skill-with-tricky-patterns")
    assert_eq(result["metrics"]["security_scan"]["skipped"], False, "security_scan.skipped")


# --- reconcile_reviews.py: the consistency-runs worked example ---
@check("reconcile_reviews: 3-run consensus is needs_work, not run 1's solo blocked")
def _():
    runs_dir = FIXTURES / "consistency-runs"
    result = run_json(
        SCRIPTS / "reconcile_reviews.py",
        runs_dir / "example-skill-review-run1.json",
        runs_dir / "example-skill-review-run2.json",
        runs_dir / "example-skill-review-run3.json",
    )
    assert_eq(result["overall_verdict"], "needs_work", "overall_verdict")
    assert_eq(result["overall_verdict_by_run"][0], "blocked", "overall_verdict_by_run[0] (run 1 alone)")
    assert_eq(result["confirmed_findings_count"], 3, "confirmed_findings_count")
    assert_eq(result["unconfirmed_findings_count"], 2, "unconfirmed_findings_count")
    safety_finding = next(f for f in result["findings"] if f["category"] == "safety")
    assert_eq(safety_finding["confirmed"], False, "the one-off safety finding's confirmed status")
    assert_eq(safety_finding["agreement_count"], 1, "the one-off safety finding's agreement_count")


# --- diff_reviews.py: deterministic mode (two skill directories) ---
@check("diff_reviews (deterministic): diff-old-skill -> diff-new-skill is 1 new, 3 resolved, 3 unchanged")
def _():
    result = run_json(
        SCRIPTS / "diff_reviews.py", FIXTURES / "diff-old-skill", FIXTURES / "diff-new-skill",
    )
    assert_eq(result["mode"], "deterministic", "mode")
    assert_eq(len(result["new_findings"]), 1, "len(new_findings)")
    assert_eq(result["new_findings"][0]["check_id"], "orphaned_resource_file", "new_findings[0].check_id")
    assert_eq(len(result["resolved_findings"]), 3, "len(resolved_findings)")
    assert_eq(result["unchanged_findings_count"], 3, "unchanged_findings_count")


@check("diff_reviews (deterministic): --fail-on-new exits 1 when a new finding is introduced")
def _():
    _, returncode, _ = run(
        SCRIPTS / "diff_reviews.py", FIXTURES / "diff-old-skill", FIXTURES / "diff-new-skill", "--fail-on-new",
    )
    assert_eq(returncode, 1, "exit code")


@check("diff_reviews (deterministic): --fail-on-new exits 0 when no new finding is introduced")
def _():
    _, returncode, _ = run(
        SCRIPTS / "diff_reviews.py", FIXTURES / "diff-new-skill", FIXTURES / "diff-new-skill", "--fail-on-new",
    )
    assert_eq(returncode, 0, "exit code (comparing a directory against itself)")


# --- diff_reviews.py: qualitative mode (two review.json files) ---
@check("diff_reviews (qualitative): version-diff old -> new is 1 new, 1 resolved, 1 severity-changed, 1 unchanged")
def _():
    runs_dir = FIXTURES / "version-diff"
    result = run_json(
        SCRIPTS / "diff_reviews.py",
        runs_dir / "example-skill-review-old.json",
        runs_dir / "example-skill-review-new.json",
    )
    assert_eq(result["mode"], "qualitative", "mode")
    assert_eq(result["overall_verdict"]["old"], "needs_work", "overall_verdict.old")
    assert_eq(result["overall_verdict"]["new"], "pass_with_suggestions", "overall_verdict.new")
    assert_eq(len(result["new_findings"]), 1, "len(new_findings)")
    assert_eq(len(result["resolved_findings"]), 1, "len(resolved_findings)")
    assert_eq(len(result["severity_changed_findings"]), 1, "len(severity_changed_findings)")
    assert_eq(result["severity_changed_findings"][0]["old_severity"], "major", "severity_changed_findings[0].old_severity")
    assert_eq(result["severity_changed_findings"][0]["new_severity"], "minor", "severity_changed_findings[0].new_severity")
    assert_eq(result["unchanged_findings_count"], 1, "unchanged_findings_count")


@check("diff_reviews: rejects mixing a skill directory with a review.json file")
def _():
    stdout, _, _ = run(
        SCRIPTS / "diff_reviews.py",
        FIXTURES / "good-skill", FIXTURES / "version-diff" / "example-skill-review-new.json",
    )
    result = json.loads(stdout)
    assert "fatal_error" in result, f"expected fatal_error for mixed dir+file input, got: {result}"


# ============================================================
# Cost/execution layer (skill-eval's own, pre-merge)
# ============================================================

# --- models_config.yaml: loading and shape ---
@check("models_config.yaml: loads and has a non-empty default_models list including sonnet")
def _():
    import yaml
    data = yaml.safe_load((ROOT / "references" / "models_config.yaml").read_text(encoding="utf-8"))
    models = data.get("default_models")
    assert_true(isinstance(models, list) and len(models) > 0, "default_models should be a non-empty list")
    assert_true("sonnet" in models, "default_models should include 'sonnet' by default")


# --- render_report.py: table rendering from a fixed, hand-written sample input ---
@check("render_report.py: renders model/tokens/time/judgment correctly, escapes a pipe in a bullet")
def _():
    stdout, returncode, stderr = run(SCRIPTS / "render_report.py", FIXTURES / "render-report-sample.json")
    assert_eq(returncode, 0, f"exit code (stderr: {stderr.strip()})")
    assert_in("sample-skill", stdout, "skill_name in header")
    assert_in("sonnet", stdout, "model name")
    assert_in("~1,234 (estimated)", stdout, "estimated token formatting")
    assert_in("12.5s", stdout, "time formatting")
    assert_in("First bullet, a concrete observation.", stdout, "first judgment bullet")
    assert_in("a \\| pipe character", stdout, "pipe character escaped, not breaking the table")
    assert_in("1 structural warning(s)", stdout, "gate-check stage 1a note")
    assert_in("pass_with_suggestions", stdout, "gate-check stage 1b verdict")


@check("render_report.py: zero runs renders 'No runs recorded.' instead of an empty table")
def _():
    stdout, returncode, stderr = run(SCRIPTS / "render_report.py", FIXTURES / "render-report-empty.json")
    assert_eq(returncode, 0, f"exit code (stderr: {stderr.strip()})")
    assert_in("No runs recorded.", stdout, "empty-runs message")


# ============================================================
# Self-check and packaging
# ============================================================

@check("skill-eval: zero compliance errors against its own directory")
def _():
    result = run_json(SCRIPTS / "structural_check.py", ROOT)
    assert_eq(result["compliance_errors"], [], "compliance_errors")


@check("skill-eval: packages cleanly via the shared package_skill.py")
def _():
    stdout, returncode, stderr = run(ROOT.parent / "scripts" / "package_skill.py", ROOT, ROOT / "dist")
    assert_eq(returncode, 0, f"exit code (stderr: {stderr.strip()})")
    data = json.loads(stdout)
    assert_eq(data.get("skill_name"), "skill-eval", "packaged skill_name")


def main():
    print(f"skill-eval regression suite — {_checks_run} check(s) run, "
          f"{_checks_run - len(_failures)} passed, {len(_failures)} failed.")
    if _failures:
        print("\nFailed:")
        for name in _failures:
            print(f"  - {name}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
