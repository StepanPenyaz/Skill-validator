#!/usr/bin/env python3
"""
render_report.py — renders skill-eval's collected run data as the final
Markdown report: one table, one row per model tested.

Purely mechanical, like skill-review/scripts/generate_static_report.py: by
the time this runs, Workflow steps 1-3 have already collected everything
it needs (the gate-check result, model/tokens/time per run, and a
judgment Claude wrote in step 3) — this script does no judging of its
own, just formatting. No model call, no PyYAML dependency (input is JSON).

Usage:
    python3 render_report.py <input.json> [--out <path>]

<input.json> shape:
{
  "skill_name": "example-skill",
  "gate_check": {
    "stage_1a": {"structural_warnings_count": 2},
    "stage_1b": {"overall_verdict": "pass_with_suggestions"}
  },
  "runs": [
    {
      "model": "sonnet",
      "tokens": 1850,
      "tokens_estimated": true,
      "time_seconds": 42.3,
      "judgment": ["bullet one", "bullet two", "bullet three"]
    }
  ]
}

`gate_check` is optional context (renders as a blockquote note above the
table) but always present in real use — Workflow step 1 always ran, and
passed, before step 4 is ever reached; a failed gate check stops the whole
Workflow before any report is rendered. `runs[].tokens_estimated` controls
whether the "Number of Tokens" cell is labeled `(estimated)` — see
references/token-capture.md for why it's an estimate today.

Prints Markdown to stdout, or writes it to --out if given.
"""

import json
import sys
from pathlib import Path

# On Windows, stdout otherwise defaults to the console's codepage (commonly
# cp1252), which can't represent the bullet character or em dashes used
# below — same fix as skill-review/scripts/generate_static_report.py.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


def fail(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def esc(text):
    """Markdown table cells break on a literal '|' or embedded newline —
    same escaping generate_static_report.py applies to finding text."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def format_time(seconds):
    if seconds is None:
        return "-"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}m {secs:.0f}s"


def format_tokens(tokens, estimated):
    if tokens is None:
        return "-"
    formatted = f"{tokens:,}"
    return f"~{formatted} (estimated)" if estimated else formatted


def format_judgment(bullets):
    if not bullets:
        return "(no judgment recorded)"
    return "<br>".join(f"\u2022 {esc(b)}" for b in bullets)


def render_gate_check_note(gate_check):
    """Always shown, even though every real report implies the gate check
    passed (a failed gate check stops the Workflow before step 4 runs) —
    the report should be self-contained, not require re-running gate mode
    to know it happened at all. See skill-eval/SKILL.md Decision
    Guidelines on surfacing a non-blocking gate result."""
    if not gate_check:
        return ""
    lines = ["> **Gate check** (via skill-review) — passed, evaluation proceeded:"]
    stage_1a = gate_check.get("stage_1a") or {}
    warnings = stage_1a.get("structural_warnings_count", 0)
    if warnings:
        lines.append(f"> - Stage 1a (deterministic): {warnings} structural warning(s), not blocking.")
    else:
        lines.append("> - Stage 1a (deterministic): zero structural warnings.")
    stage_1b = gate_check.get("stage_1b") or {}
    verdict = stage_1b.get("overall_verdict")
    if verdict:
        lines.append(f"> - Stage 1b (qualitative): `overall_verdict` = `{verdict}`, not blocking.")
    return "\n".join(lines) + "\n"


def render_markdown(data):
    skill_name = data.get("skill_name", "unknown-skill")
    runs = data.get("runs", [])

    lines = [f"# skill-eval Report: {skill_name}", ""]

    gate_note = render_gate_check_note(data.get("gate_check"))
    if gate_note:
        lines.append(gate_note)

    if not runs:
        lines.append("No runs recorded.")
        return "\n".join(lines) + "\n"

    lines.append("| Model Used | Number of Tokens | Time Spent | Claude's Judgment |")
    lines.append("|---|---:|---:|---|")
    for run in runs:
        model = esc(run.get("model", "?"))
        tokens = format_tokens(run.get("tokens"), run.get("tokens_estimated", False))
        time_spent = format_time(run.get("time_seconds"))
        judgment = format_judgment(run.get("judgment"))
        lines.append(f"| {model} | {tokens} | {time_spent} | {judgment} |")

    return "\n".join(lines).rstrip() + "\n"


def main():
    args = sys.argv[1:]
    out_path = None
    if "--out" in args:
        idx = args.index("--out")
        if idx + 1 >= len(args):
            fail("--out requires a path argument.")
        out_path = args[idx + 1]
        del args[idx:idx + 2]

    if len(args) != 1:
        fail("Usage: python render_report.py <input.json> [--out <path>]")

    input_path = Path(args[0])
    if not input_path.is_file():
        fail(f"Not a file: {input_path}")

    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON in {input_path}: {e}")

    report = render_markdown(data)

    if out_path:
        Path(out_path).write_text(report, encoding="utf-8")
        print(f"Wrote {out_path}")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
