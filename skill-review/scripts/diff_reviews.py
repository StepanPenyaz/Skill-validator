#!/usr/bin/env python3
"""
diff_reviews.py — diffs skill-review's output across two versions of a
skill, per SKILL.md's Decision Guidelines: "the JSON output is designed to
be diffed across versions." Fills the gap between that claim and what was
actually shipped: previously this diffing was a manual, by-hand process
with a separate external tool.

Two modes, auto-detected from what <old> and <new> point to:

- Two skill DIRECTORIES -> deterministic mode. Runs structural_check.py
  against each and diffs compliance_errors, structural_warnings, and
  findings (grouped by check_id + location). No model call, works
  standalone — this is what a CI gate wants: fail a PR only on NEWLY
  INTRODUCED findings (--fail-on-new), not on pre-existing ones.
- Two <skill-name>-review.json FILES (the qualitative Static Quality
  output, per references/schema.md) -> qualitative mode. Diffs
  overall_verdict, category_scores, and findings (grouped by category +
  location), including a severity change on a finding that persists across
  versions — something the deterministic layer can't have, since its
  severities are fixed per check_id by severity_config.yaml, not assigned
  per instance the way a model's qualitative judgment is.

Mixing one directory and one review.json is rejected: there's no shared
schema to diff them against.

Usage:
    python3 diff_reviews.py <old> <new> [--markdown] [--fail-on-new] \
        [--force-security-scan] [--out <path>]

Prints one JSON object (or Markdown with --markdown) to stdout, or writes
it to --out if given. --fail-on-new exits 1 if <new> has any finding that
wasn't in <old> — for a CI gate that should only block on regressions a PR
actually introduced. --force-security-scan is passed through to
structural_check.py in deterministic mode only.
"""

import json
import sys
from pathlib import Path

# On Windows, stdout otherwise defaults to the console's codepage (commonly
# cp1252), which can't represent the em dashes/arrows used in the Markdown
# output — same fix as generate_static_report.py and run_regression.py.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import structural_check as sc
from reconcile_reviews import load_run  # reuses the qualitative-schema field validation


def fail(msg):
    print(json.dumps({"fatal_error": msg}))
    sys.exit(1)


def det_finding_key(f):
    """(check_id, location) normally; falls back to (check_id, issue) when
    location is None so two distinct no-location findings under the same
    check_id (e.g. two different undeclared_external_host hits) don't
    collide into a single diff entry."""
    return (f["check_id"], f["location"] if f["location"] else f["issue"])


def diff_deterministic(old_path, new_path, force_security_scan=False):
    old_result = sc.run_checks(old_path, force_security_scan=force_security_scan)
    if "fatal_error" in old_result:
        fail(f"structural_check.py failed on {old_path}: {old_result['fatal_error']}")
    new_result = sc.run_checks(new_path, force_security_scan=force_security_scan)
    if "fatal_error" in new_result:
        fail(f"structural_check.py failed on {new_path}: {new_result['fatal_error']}")

    old_by_key = {det_finding_key(f): f for f in old_result["findings"]}
    new_by_key = {det_finding_key(f): f for f in new_result["findings"]}
    new_keys = set(new_by_key) - set(old_by_key)
    resolved_keys = set(old_by_key) - set(new_by_key)
    unchanged_keys = set(new_by_key) & set(old_by_key)

    old_skipped = old_result["metrics"]["security_scan"]["skipped"]
    new_skipped = new_result["metrics"]["security_scan"]["skipped"]

    return {
        "mode": "deterministic",
        "old_path": str(old_path),
        "new_path": str(new_path),
        "compliance_errors_delta": {
            "old_count": len(old_result["compliance_errors"]),
            "new_count": len(new_result["compliance_errors"]),
        },
        "structural_warnings_delta": {
            "old_count": len(old_result["structural_warnings"]),
            "new_count": len(new_result["structural_warnings"]),
        },
        "security_scan": {
            "old_skipped": old_skipped,
            "new_skipped": new_skipped,
            "changed": old_skipped != new_skipped,
        },
        "new_findings": [new_by_key[k] for k in sorted(new_keys, key=str)],
        "resolved_findings": [old_by_key[k] for k in sorted(resolved_keys, key=str)],
        "unchanged_findings_count": len(unchanged_keys),
    }


def qual_finding_key(f):
    """(category, location) normally; falls back to (category, issue) when
    location is None — same reasoning as det_finding_key above."""
    location = f.get("location")
    return (f.get("category"), location if location else f.get("issue"))


def diff_qualitative(old_path, new_path):
    old = load_run(old_path)
    new = load_run(new_path)

    all_categories = sorted(set(old["category_scores"]) | set(new["category_scores"]))
    category_scores = {}
    for category in all_categories:
        old_value = old["category_scores"].get(category)
        new_value = new["category_scores"].get(category)
        category_scores[category] = {
            "old": old_value, "new": new_value, "changed": old_value != new_value,
        }

    old_by_key = {qual_finding_key(f): f for f in old["findings"]}
    new_by_key = {qual_finding_key(f): f for f in new["findings"]}
    new_keys = set(new_by_key) - set(old_by_key)
    resolved_keys = set(old_by_key) - set(new_by_key)
    persisting_keys = set(new_by_key) & set(old_by_key)

    severity_changed = []
    unchanged_count = 0
    for key in persisting_keys:
        old_finding, new_finding = old_by_key[key], new_by_key[key]
        if old_finding["severity"] != new_finding["severity"]:
            severity_changed.append({
                "category": new_finding.get("category"),
                "location": new_finding.get("location"),
                "old_severity": old_finding["severity"],
                "new_severity": new_finding["severity"],
                "issue": new_finding.get("issue"),
            })
        else:
            unchanged_count += 1
    severity_changed.sort(key=lambda f: (f["category"] or "", f["location"] or ""))

    return {
        "mode": "qualitative",
        "old_path": str(old_path),
        "new_path": str(new_path),
        "old_skill_name": old["skill_name"],
        "new_skill_name": new["skill_name"],
        "overall_verdict": {
            "old": old["overall_verdict"],
            "new": new["overall_verdict"],
            "changed": old["overall_verdict"] != new["overall_verdict"],
        },
        "category_scores": category_scores,
        "new_findings": [new_by_key[k] for k in sorted(new_keys, key=str)],
        "resolved_findings": [old_by_key[k] for k in sorted(resolved_keys, key=str)],
        "severity_changed_findings": severity_changed,
        "unchanged_findings_count": unchanged_count,
    }


def esc(value):
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render_markdown(diff):
    lines = []
    if diff["mode"] == "deterministic":
        lines.append(f"# Diff: `{diff['old_path']}` -> `{diff['new_path']}` (deterministic)")
        lines.append("")
        ced, swd = diff["compliance_errors_delta"], diff["structural_warnings_delta"]
        lines.append(f"Compliance errors: {ced['old_count']} -> {ced['new_count']}  ")
        lines.append(f"Structural warnings: {swd['old_count']} -> {swd['new_count']}  ")
        ss = diff["security_scan"]
        if ss["changed"]:
            lines.append(f"Security scan skipped: {ss['old_skipped']} -> {ss['new_skipped']}  ")
        lines.append("")
        lines.append(
            f"{len(diff['new_findings'])} new finding(s), {len(diff['resolved_findings'])} "
            f"resolved, {diff['unchanged_findings_count']} unchanged."
        )
        header = "| Check | Severity | Issue | Location |"
        sep = "|---|---|---|---|"
        for title, findings in (("New findings", diff["new_findings"]),
                                 ("Resolved findings", diff["resolved_findings"])):
            if not findings:
                continue
            lines += ["", f"## {title}", "", header, sep]
            for f in findings:
                lines.append(f"| {esc(f['check_id'])} | {esc(f['severity'])} | {esc(f['issue'])} | {esc(f.get('location'))} |")
    else:
        lines.append(f"# Diff: {diff['old_skill_name']} -> {diff['new_skill_name']} (qualitative)")
        lines.append("")
        ov = diff["overall_verdict"]
        lines.append(f"Overall verdict: {ov['old']} -> {ov['new']}{' (changed)' if ov['changed'] else ''}")
        lines += ["", "## Category scores", "", "| Category | Old | New | Changed |", "|---|---|---|---|"]
        for category, v in diff["category_scores"].items():
            lines.append(f"| {esc(category)} | {esc(v['old'])} | {esc(v['new'])} | {'yes' if v['changed'] else ''} |")
        lines.append("")
        lines.append(
            f"{len(diff['new_findings'])} new finding(s), {len(diff['resolved_findings'])} resolved, "
            f"{len(diff['severity_changed_findings'])} severity-changed, "
            f"{diff['unchanged_findings_count']} unchanged."
        )
        header = "| Category | Severity | Issue | Location |"
        sep = "|---|---|---|---|"
        for title, findings in (("New findings", diff["new_findings"]),
                                 ("Resolved findings", diff["resolved_findings"])):
            if not findings:
                continue
            lines += ["", f"## {title}", "", header, sep]
            for f in findings:
                lines.append(f"| {esc(f.get('category'))} | {esc(f.get('severity'))} | {esc(f.get('issue'))} | {esc(f.get('location'))} |")
        if diff["severity_changed_findings"]:
            lines += ["", "## Severity changed", "",
                      "| Category | Old Severity | New Severity | Issue | Location |", "|---|---|---|---|---|"]
            for f in diff["severity_changed_findings"]:
                lines.append(
                    f"| {esc(f['category'])} | {esc(f['old_severity'])} | {esc(f['new_severity'])} | "
                    f"{esc(f['issue'])} | {esc(f['location'])} |"
                )
    return "\n".join(lines).rstrip() + "\n"


def main():
    args = sys.argv[1:]
    markdown = "--markdown" in args
    if markdown:
        args = [a for a in args if a != "--markdown"]
    fail_on_new = "--fail-on-new" in args
    if fail_on_new:
        args = [a for a in args if a != "--fail-on-new"]
    force_security_scan = "--force-security-scan" in args
    if force_security_scan:
        args = [a for a in args if a != "--force-security-scan"]
    out_path = None
    if "--out" in args:
        idx = args.index("--out")
        if idx + 1 >= len(args):
            fail("--out requires a path argument.")
        out_path = args[idx + 1]
        del args[idx:idx + 2]

    if len(args) != 2:
        fail(
            "Usage: python diff_reviews.py <old> <new> [--markdown] [--fail-on-new] "
            "[--force-security-scan] [--out <path>]"
        )

    old_arg, new_arg = Path(args[0]), Path(args[1])
    old_is_dir, new_is_dir = old_arg.is_dir(), new_arg.is_dir()
    old_is_file, new_is_file = old_arg.is_file(), new_arg.is_file()

    if not (old_is_dir or old_is_file):
        fail(f"Not a file or directory: {old_arg}")
    if not (new_is_dir or new_is_file):
        fail(f"Not a file or directory: {new_arg}")

    if old_is_dir and new_is_dir:
        diff = diff_deterministic(old_arg, new_arg, force_security_scan=force_security_scan)
    elif old_is_file and new_is_file:
        diff = diff_qualitative(old_arg, new_arg)
    else:
        fail(
            "Both arguments must be the same kind: two skill directories (deterministic "
            "diff) or two <skill-name>-review.json files (qualitative diff). Got "
            f"old={'directory' if old_is_dir else 'file'}, new={'directory' if new_is_dir else 'file'}."
        )

    output = render_markdown(diff) if markdown else json.dumps(diff, indent=2)

    if out_path:
        Path(out_path).write_text(output, encoding="utf-8")
    else:
        print(output)

    if fail_on_new and diff["new_findings"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
