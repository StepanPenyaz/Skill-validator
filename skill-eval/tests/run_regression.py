#!/usr/bin/env python3
"""
run_regression.py — skill-eval's own regression suite.

Covers the parts of skill-eval that are actually deterministic/scriptable:
- The gate-check stop condition's underlying signal — skill-review's own
  structural_check.py, which skill-eval's Workflow step 1a runs and reads
  compliance_errors from to decide whether to stop.
- references/models_config.yaml loading and shape.
- scripts/render_report.py's table rendering from a fixed, hand-written
  sample input (and the zero-runs edge case).
- Self-check: skill-eval's own SKILL.md passes skill-review's gate mode.
- Packaging: skill-eval still packages cleanly.

Explicitly out of scope, same reasoning skill-review's own suite uses:
anything requiring a live model call — task execution (Workflow step 2),
judgment-writing (step 3), or skill-review's own qualitative full review
mode (stage 1b). Those aren't scriptable this way.

Same style as skill-review/tests/run_regression.py: plain assertions over
subprocess calls to real CLI entrypoints, no test framework, stdlib only
(PyYAML is already a stated dependency, same as skill-review).

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
# fix as skill-review/tests/run_regression.py and scripts/render_report.py.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent  # skill-eval/
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
SKILL_REVIEW = ROOT.parent / "skill-review"

_failures = []
_checks_run = 0


def run(*args):
    """Runs `python3 <args>` exactly as a user would, returning (stdout, returncode).
    Raises AssertionError (not a bare crash) on nothing — callers decide what
    counts as failure, since some checks here want a non-zero exit."""
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


# --- Gate-check stop condition: the deterministic signal Workflow step 1a relies on ---
@check("gate-check signal: bad-skill has compliance_errors (skill-eval must stop, never proceed)")
def _():
    result = run_json(
        SKILL_REVIEW / "scripts" / "structural_check.py",
        SKILL_REVIEW / "tests" / "fixtures" / "bad-skill",
    )
    assert_true(len(result["compliance_errors"]) > 0, "bad-skill's compliance_errors should be non-empty")


@check("gate-check signal: clean-skill-with-tricky-patterns has zero compliance_errors (1a may pass)")
def _():
    result = run_json(
        SKILL_REVIEW / "scripts" / "structural_check.py",
        SKILL_REVIEW / "tests" / "fixtures" / "clean-skill-with-tricky-patterns",
    )
    assert_eq(result["compliance_errors"], [], "compliance_errors")


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


# --- Self-check: skill-eval's own SKILL.md passes skill-review's gate mode ---
@check("skill-eval: zero compliance errors against its own directory")
def _():
    result = run_json(SKILL_REVIEW / "scripts" / "structural_check.py", ROOT)
    assert_eq(result["compliance_errors"], [], "compliance_errors")


# --- Packaging: skill-eval still packages cleanly ---
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
