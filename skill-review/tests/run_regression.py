#!/usr/bin/env python3
"""
run_regression.py — skill-review's own regression suite.

Runs scripts/structural_check.py and scripts/reconcile_reviews.py against
every fixture under tests/fixtures/ (plus skill-review's own directory)
exactly as documented in README.md's "Local testing" section, and asserts
the result matches what's documented there — instead of a human re-running
each command by hand and eyeballing the output before every change to
structural_check.py, severity_config.yaml, reconcile_reviews.py, or a
fixture.

Deliberately plain assertions over subprocess calls to the real CLI
entrypoints, not pytest and not imported internals — this exercises the
exact commands a user would run (catching CLI-arg-parsing bugs, not just
internal-function bugs), and stays dependency-free like everything else
under skill-review/ (stdlib only, JSON in/out, same as structural_check.py
itself).

Usage:
    python3 tests/run_regression.py

Exits 0 if every check passes; 1 (after printing every failure, not just
the first) otherwise.
"""

import json
import subprocess
import sys
from pathlib import Path

# On Windows, stdout otherwise defaults to the console's codepage (commonly
# cp1252), which can't represent the em dashes used below — same fix as
# scripts/generate_static_report.py.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent  # skill-review/
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"

_failures = []
_checks_run = 0


def run_json(script_name, *args):
    """Runs `python3 scripts/<script_name> <args>`, exactly as a user would
    per README.md, and parses stdout as JSON. Raises AssertionError (not a
    bare crash) on a non-zero exit or invalid JSON, so a single broken
    command shows up as one clear failure line instead of aborting the
    whole suite."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script_name), *(str(a) for a in args)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"{script_name} {' '.join(str(a) for a in args)} exited {proc.returncode}: "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"{script_name} {' '.join(str(a) for a in args)} did not print valid JSON ({e}): "
            f"{proc.stdout[:300]!r}"
        )


def check(name):
    """Decorator: registers `fn` as one named regression check. Runs it
    immediately, catching AssertionError so one failing check doesn't stop
    the rest of the suite from running (and reporting) too."""
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


def assert_check_ids(findings, expected_ids, label):
    """Asserts `findings` contains at least one finding for every check_id
    in expected_ids — set-based (a check firing more than once, e.g.
    must_never_line on 4 separate lines, is still one entry in this set),
    so this verifies each SPECIFIC documented issue was actually caught,
    not just that the raw finding count didn't change (which would miss a
    check silently breaking while an unrelated one started over-firing by
    the same amount)."""
    actual_ids = {f["check_id"] for f in findings}
    missing = sorted(set(expected_ids) - actual_ids)
    if missing:
        raise AssertionError(f"{label}: missing expected check_id(s) {missing}; got {sorted(actual_ids)}")


# --- good-skill: should be entirely clean, including the two soft (Info) checks ---
@check("good-skill: zero compliance errors and zero structural warnings")
def _():
    result = run_json("structural_check.py", FIXTURES / "good-skill")
    assert_eq(result["compliance_errors"], [], "compliance_errors")
    assert_eq(result["structural_warnings"], [], "structural_warnings")
    assert_eq(result["findings"], [], "findings")


@check("good-skill: security scan skipped (no shell/network tool declared or referenced)")
def _():
    result = run_json("structural_check.py", FIXTURES / "good-skill")
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
    result = run_json("structural_check.py", FIXTURES / "bad-skill")
    assert_check_ids(result["findings"], BAD_SKILL_EXPECTED_CHECK_IDS, "bad-skill findings")


@check("bad-skill: hardcoded secret is a Blocker (compliance_errors), not just a Warning")
def _():
    result = run_json("structural_check.py", FIXTURES / "bad-skill")
    secret_findings = [f for f in result["findings"] if f["check_id"] == "hardcoded_secret"]
    assert len(secret_findings) >= 1, "expected at least one hardcoded_secret finding"
    assert_eq(secret_findings[0]["severity"], "Blocker", "hardcoded_secret severity")
    assert len(result["compliance_errors"]) >= 1, "expected compliance_errors to be non-empty"


@check("bad-skill: security scan NOT skipped (declares WebSearch, references Bash)")
def _():
    result = run_json("structural_check.py", FIXTURES / "bad-skill")
    assert_eq(result["metrics"]["security_scan"]["skipped"], False, "security_scan.skipped")


# --- clean-skill-with-tricky-patterns: precision test, must stay silent ---
@check("clean-skill-with-tricky-patterns: zero findings despite surface-similar-to-bad patterns")
def _():
    result = run_json("structural_check.py", FIXTURES / "clean-skill-with-tricky-patterns")
    assert_eq(result["compliance_errors"], [], "compliance_errors")
    assert_eq(result["structural_warnings"], [], "structural_warnings")
    assert_eq(result["findings"], [], "findings")


@check("clean-skill-with-tricky-patterns: security scan NOT skipped (declares+references Bash)")
def _():
    result = run_json("structural_check.py", FIXTURES / "clean-skill-with-tricky-patterns")
    assert_eq(result["metrics"]["security_scan"]["skipped"], False, "security_scan.skipped")


# --- skill-review itself: self-check, per the long-standing documented contract ---
@check("skill-review: zero compliance errors against its own directory")
def _():
    result = run_json("structural_check.py", ROOT)
    assert_eq(result["compliance_errors"], [], "compliance_errors")


# --- reconcile_reviews.py: the consistency-runs worked example ---
@check("reconcile_reviews: 3-run consensus is needs_work, not run 1's solo blocked")
def _():
    runs_dir = FIXTURES / "consistency-runs"
    result = run_json(
        "reconcile_reviews.py",
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


def main():
    print(f"skill-review regression suite — {_checks_run} check(s) run, "
          f"{_checks_run - len(_failures)} passed, {len(_failures)} failed.")
    if _failures:
        print("\nFailed:")
        for name in _failures:
            print(f"  - {name}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
