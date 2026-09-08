#!/usr/bin/env python3
"""
generate_static_report.py — renders structural_check.py's findings as a
human-readable Markdown report: one table per category (Metadata, Structure,
Permissions & Tool Usage, Security), each row showing what's wrong, its
severity (Blocker/Warning/Info), and a suggested fix.

This is still the deterministic Linter stage — every row is a raw pattern
match from structural_check.py, with no qualitative judgment applied. It is
NOT the final <skill-name>-review.md produced by the qualitative Static
Quality pass (see SKILL.md Step 5) — that step still needs to confirm each
Warning/Info-level candidate against real context before treating it as a
scored finding.

Usage:
    python generate_static_report.py <skill_directory> [--out <path>]

Prints Markdown to stdout, or writes it to --out if given.
"""

import sys
from pathlib import Path

# On Windows, stdout otherwise defaults to the console's codepage (commonly
# cp1252), which can't represent characters like em dashes or the "…" used
# to mark redacted secret values below — reconfigure to UTF-8 explicitly.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import structural_check as sc

CATEGORY_ORDER = [
    sc.CATEGORY_METADATA,
    sc.CATEGORY_STRUCTURE,
    sc.CATEGORY_PERMISSIONS,
    sc.CATEGORY_SECURITY,
]
SEVERITY_ORDER = {"Blocker": 0, "Warning": 1, "Info": 2}


def render_markdown_report(skill_name, findings):
    counts = {"Blocker": 0, "Warning": 0, "Info": 0}
    for f in findings:
        counts[f["severity"]] += 1

    lines = [
        f"# Static Check Report: {skill_name}",
        "",
        f"{counts['Blocker']} blocker(s), {counts['Warning']} warning(s), "
        f"{counts['Info']} info-level suggestion(s).",
        "",
    ]

    if not findings:
        lines.append("No issues found by the static checker.")
        return "\n".join(lines) + "\n"

    by_category = {c: [] for c in CATEGORY_ORDER}
    for f in findings:
        by_category.setdefault(f["category"], []).append(f)

    for category in CATEGORY_ORDER:
        items = by_category.get(category, [])
        if not items:
            continue
        items = sorted(items, key=lambda f: SEVERITY_ORDER[f["severity"]])
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| What's Wrong | Severity | Suggested Fix |")
        lines.append("|---|---|---|")
        for f in items:
            what = f["issue"].replace("|", "\\|").replace("\n", " ")
            if f.get("location"):
                what = f"`{f['location']}` — {what}"
            suggestion = f["suggestion"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {what} | {f['severity']} | {suggestion} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    if len(sys.argv) < 2:
        print("Error: Usage: python generate_static_report.py <skill_directory> [--out <path>]",
              file=sys.stderr)
        sys.exit(1)

    skill_dir = sys.argv[1]
    out_path = None
    if "--out" in sys.argv:
        idx = sys.argv.index("--out")
        if idx + 1 >= len(sys.argv):
            print("Error: --out requires a path argument.", file=sys.stderr)
            sys.exit(1)
        out_path = sys.argv[idx + 1]

    skill_path = Path(skill_dir)
    if not skill_path.is_dir():
        print(f"Error: Not a directory: {skill_path}", file=sys.stderr)
        sys.exit(1)

    result = sc.run_checks(skill_path)
    if "fatal_error" in result:
        print(f"Error: {result['fatal_error']}", file=sys.stderr)
        sys.exit(1)

    skill_name = result["frontmatter"].get("name") or skill_path.name
    report = render_markdown_report(skill_name, result["findings"])

    if out_path:
        Path(out_path).write_text(report, encoding="utf-8")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
