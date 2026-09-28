#!/usr/bin/env python3
"""
render_report.py — renders skill-eval's collected run data as the final
Markdown report.

Purely mechanical, like this skill's own scripts/generate_static_report.py
and scripts/diff_reviews.py (both reused here, not reimplemented — see
below): by the time this runs, Workflow steps 1-3 have already collected
everything it needs (the static-review result, model/tokens/time per run,
and a judgment Claude wrote in step 3) — this script does no judging of
its own, just formatting. No model call, no PyYAML dependency (input is
JSON).

Usage:
    python3 render_report.py <input.json> [--out <path>]

Two report shapes, auto-detected from `report_type` (default "single"):

## Single-skill report (`report_type` absent or "single")

{
  "skill_name": "example-skill",
  "gate_check": {
    "stage_1a": {
      "structural_warnings_count": 2, "compliance_errors": [],
      "findings": [{"category": "...", "severity": "Warning", "issue": "...",
                     "suggestion": "...", "location": null}],
      "security_scan": {"skipped": true, "reason": "...", "checks_skipped": [...]}
    },
    "stage_1b": {
      "overall_verdict": "pass_with_suggestions", "blocked_categories": [],
      "category_scores": {"safety": "pass", "...": "..."},
      "review_file": "example-skill-review.md"
    }
  },
  "task_fixture_auto_generated": false,
  "runs": [
    {
      "model": "sonnet",
      "tokens": 1850,
      "tokens_estimated": true,
      "time_seconds": 42.3,
      "cost_usd": 0.0111,
      "judgment": ["bullet one", "bullet two", "bullet three"]
    }
  ]
}

`runs[].cost_usd` is optional (a run without it renders "-" in the Cost
column) — see references/models_config.yaml's Pricing section for how
it's computed (tokens x that model's blended $/M rate) and why it's a
labeled estimate, never an exact bill line item, since `subagent_tokens`
doesn't split input vs. output tokens. A single-skill report with any
`cost_usd` present sums them into a "Total cost" line below the table.

`gate_check` is optional context (renders as a blockquote note, plus a
"Static Check Findings"/"Qualitative Review Summary" section when
`stage_1a.findings`/`stage_1b.category_scores` are given) but always
present in real use. The static review no longer stops the run on a
Blocker/`blocked` verdict (see SKILL.md's Rules) — Workflow always
proceeds to step 2 and this report always gets rendered, so
`stage_1a.compliance_errors` (non-empty) and a `stage_1b.overall_verdict`
of `blocked` are real possibilities here, not just theoretical. When
either is present, the gate-check note renders as a prominent warning
instead of the routine "passed, evaluation proceeded" note.
`stage_1a.findings` is rendered via generate_static_report.py's own
`render_markdown_report` (imported, not reimplemented) so the two never
drift apart. `stage_1b.review_file` points at the full qualitative
findings/rewrites file rather than duplicating it inline here.

`task_fixture_auto_generated: true` renders a note that no task fixture
existed yet for this skill and one was authored automatically this run —
see SKILL.md Workflow step 2 and references/task-authoring.md.

## Comparative report (`report_type: "comparative"`, two skill versions)

{
  "report_type": "comparative",
  "old_skill_name": "example-skill-v3", "new_skill_name": "example-skill-v4",
  "structural_diff": { ... scripts/diff_reviews.py deterministic-mode output ... },
  "qualitative_diff": { ... scripts/diff_reviews.py qualitative-mode output ... },
  "task_fixture_auto_generated": false,
  "runs": [
    {
      "model": "sonnet",
      "old": {"tokens": 1000, "tokens_estimated": false, "time_seconds": 10.0, "cost_usd": 0.006, "judgment": [...]},
      "new": {"tokens": 1200, "tokens_estimated": false, "time_seconds": 12.0, "cost_usd": 0.0072, "judgment": [...]}
    }
  ]
}

`structural_diff`/`qualitative_diff` are diff_reviews.py's own output
(deterministic and/or qualitative mode) rendered via its own
`render_markdown` (imported, not reimplemented) — either, both, or
neither may be given (a comparison run for a skill with no
`<skill-name>-review.json` on one side has no qualitative diff to show,
for instance). `runs[]` renders as one wide table, one row per model, old
vs. new side by side with a computed delta, instead of two separate
per-version tables a reader would have to line up by hand.

`runs[].{old,new}.tokens_estimated` controls whether that side's "Tokens"
value is labeled `(estimated)` — see references/token-capture.md for why
it's an estimate today. A `null` `tokens` (either side) means token
capture failed for that call — see references/token-capture.md — not that
tokens is zero. `runs[].{old,new}.cost_usd` is optional, same estimate as
the single-skill shape; a comparative report with any `cost_usd` present
sums old/new totals into a "Total cost" line after the table.

Prints Markdown to stdout, or writes it to --out if given.
"""

import json
import sys
from pathlib import Path

# On Windows, stdout otherwise defaults to the console's codepage (commonly
# cp1252), which can't represent the bullet character or em dashes used
# below — same fix as scripts/generate_static_report.py.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_static_report as gsr
import diff_reviews as dr


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
    """`tokens is None` means the `Agent` tool's result didn't carry
    `subagent_tokens` for this call (see references/token-capture.md) — a
    real gap worth calling out, not the same as "zero" or "not
    applicable," so it renders as an explicit unknown rather than silently
    reading as a dash a reader could misattribute to "no run happened"."""
    if tokens is None:
        return "unknown (capture failed — see references/token-capture.md)"
    formatted = f"{tokens:,}"
    return f"~{formatted} (estimated)" if estimated else formatted


def format_judgment(bullets):
    if not bullets:
        return "(no judgment recorded)"
    return "<br>".join(f"\u2022 {esc(b)}" for b in bullets)


def format_cost(cost_usd):
    """`cost_usd is None` means no cost was computed for this run (an older
    payload predating this field, or a model missing from
    references/models_config.yaml's pricing table) \u2014 rendered as a dash,
    not "$0.00", so it can't be misread as a free run."""
    if cost_usd is None:
        return "-"
    return f"${cost_usd:,.4f}"


def sum_costs(costs):
    """Sums the `cost_usd` values that are actually present; returns None
    (not 0) if none are, so a report with no cost data anywhere doesn't
    render a misleading "Total cost: $0.0000" line."""
    present = [c for c in costs if c is not None]
    return sum(present) if present else None


def render_gate_check_note(gate_check):
    """Always shown when gate_check is present — the report should be
    self-contained, not require re-running the static review to know what
    it found. A Blocker/`blocked` result no longer stops the Workflow (see
    SKILL.md's Rules), so this renders as a prominent warning instead of
    silently folding into the routine note, rather than disappearing."""
    if not gate_check:
        return ""
    stage_1a = gate_check.get("stage_1a") or {}
    stage_1b = gate_check.get("stage_1b") or {}
    compliance_errors = stage_1a.get("compliance_errors") or []
    verdict = stage_1b.get("overall_verdict")
    blocked_categories = stage_1b.get("blocked_categories") or []
    is_blocked = bool(compliance_errors) or verdict == "blocked"

    if is_blocked:
        lines = ["> **STATIC REVIEW FOUND BLOCKING ISSUE(S) — evaluation proceeded anyway:**"]
        if compliance_errors:
            lines.append(f"> - Stage 1a (deterministic): {len(compliance_errors)} compliance error(s):")
            for err in compliance_errors:
                lines.append(f">   - {esc(err)}")
        if verdict == "blocked":
            if blocked_categories:
                cats = ", ".join(esc(c) for c in blocked_categories)
                lines.append(f"> - Stage 1b (qualitative): `overall_verdict` = `blocked` ({cats}).")
            else:
                lines.append("> - Stage 1b (qualitative): `overall_verdict` = `blocked`.")
        lines.append(">")
        lines.append(
            "> The run below still happened against a skill with unresolved blocking "
            "issue(s) — read the results with that in mind."
        )
        return "\n".join(lines) + "\n"

    lines = ["> **Static review** (gate check) — passed, evaluation proceeded:"]
    warnings = stage_1a.get("structural_warnings_count", 0)
    if warnings:
        lines.append(f"> - Stage 1a (deterministic): {warnings} structural warning(s), not blocking.")
    else:
        lines.append("> - Stage 1a (deterministic): zero structural warnings.")
    if verdict:
        lines.append(f"> - Stage 1b (qualitative): `overall_verdict` = `{verdict}`, not blocking.")
    return "\n".join(lines) + "\n"


def render_static_findings_section(skill_name, gate_check):
    """The full deterministic findings table (category-grouped, with
    suggested fixes) — reuses generate_static_report.py's own renderer so
    this never drifts from what `structural_check.py` actually reports.
    Only rendered when the caller supplied `stage_1a.findings` — its
    absence (e.g. the sample fixtures predating this section) means "not
    given," not "zero findings," so nothing is rendered rather than a
    misleading empty table."""
    stage_1a = (gate_check or {}).get("stage_1a") or {}
    findings = stage_1a.get("findings")
    if findings is None:
        return ""
    return gsr.render_markdown_report(
        skill_name, findings, stage_1a.get("security_scan"), heading_level="##",
    ) + "\n"


def render_qualitative_summary_section(gate_check):
    """A compact overall_verdict + category_scores table pointing at the
    full <skill-name>-review.md for findings/rewrites, rather than
    duplicating that (much longer, rewrite-bearing) content inline here."""
    stage_1b = (gate_check or {}).get("stage_1b") or {}
    category_scores = stage_1b.get("category_scores")
    if not category_scores:
        return ""
    lines = ["## Qualitative Review Summary", ""]
    verdict = stage_1b.get("overall_verdict", "?")
    lines.append(f"`overall_verdict`: **{verdict}**")
    lines.append("")
    lines.append("| Category | Score |")
    lines.append("|---|---|")
    for category, score in category_scores.items():
        lines.append(f"| {esc(category)} | {esc(score)} |")
    review_file = stage_1b.get("review_file")
    if review_file:
        lines.append("")
        lines.append(f"Full findings and suggested rewrites: `{review_file}`.")
    return "\n".join(lines) + "\n\n"


def render_fixture_note(data):
    """Surfaces that Workflow step 2 had to author tests/fixtures/tasks/
    <skill-name>.yaml on the fly this run, instead of that fact silently
    disappearing once the run completes — see SKILL.md Workflow step 2."""
    if not data.get("task_fixture_auto_generated"):
        return ""
    return (
        "> No task fixture existed yet for this skill — one was authored "
        "automatically this run (see `references/task-authoring.md`) and "
        "saved for future reruns/comparisons.\n"
    )


def render_markdown(data):
    """Single-skill report: static review (gate note + findings table +
    qualitative summary) followed by one cost/judgment table, one row per
    model."""
    skill_name = data.get("skill_name", "unknown-skill")
    runs = data.get("runs", [])
    gate_check = data.get("gate_check")

    lines = [f"# skill-eval Report: {skill_name}", ""]

    gate_note = render_gate_check_note(gate_check)
    if gate_note:
        lines.append(gate_note)

    fixture_note = render_fixture_note(data)
    if fixture_note:
        lines.append(fixture_note)

    static_section = render_static_findings_section(skill_name, gate_check)
    if static_section:
        lines.append(static_section)

    qual_section = render_qualitative_summary_section(gate_check)
    if qual_section:
        lines.append(qual_section)

    if not runs:
        lines.append("No runs recorded.")
        return "\n".join(lines) + "\n"

    lines.append("| Model Used | Number of Tokens | Cost (USD) | Time Spent | Claude's Judgment |")
    lines.append("|---|---:|---:|---:|---|")
    for run in runs:
        model = esc(run.get("model", "?"))
        tokens = format_tokens(run.get("tokens"), run.get("tokens_estimated", False))
        cost = format_cost(run.get("cost_usd"))
        time_spent = format_time(run.get("time_seconds"))
        judgment = format_judgment(run.get("judgment"))
        lines.append(f"| {model} | {tokens} | {cost} | {time_spent} | {judgment} |")

    run_costs = [run.get("cost_usd") for run in runs]
    total_cost = sum_costs(run_costs)
    if total_cost is not None:
        counted = sum(1 for c in run_costs if c is not None)
        note = "" if counted == len(runs) else f" ({counted}/{len(runs)} runs had a cost figure)"
        lines.append("")
        lines.append(f"Total cost: {format_cost(total_cost)}{note}")

    return "\n".join(lines).rstrip() + "\n"


def format_tokens_pair(old_side, new_side):
    old_tokens, new_tokens = old_side.get("tokens"), new_side.get("tokens")
    old_str = format_tokens(old_tokens, old_side.get("tokens_estimated", False))
    new_str = format_tokens(new_tokens, new_side.get("tokens_estimated", False))
    if old_tokens is not None and new_tokens is not None:
        delta = new_tokens - old_tokens
        sign = "+" if delta >= 0 else ""
        return f"{old_str} \u2192 {new_str} ({sign}{delta:,})"
    return f"{old_str} \u2192 {new_str}"


def format_time_pair(old_side, new_side):
    old_seconds, new_seconds = old_side.get("time_seconds"), new_side.get("time_seconds")
    old_str, new_str = format_time(old_seconds), format_time(new_seconds)
    if old_seconds is not None and new_seconds is not None:
        delta = new_seconds - old_seconds
        sign = "+" if delta >= 0 else ""
        return f"{old_str} \u2192 {new_str} ({sign}{delta:.1f}s)"
    return f"{old_str} \u2192 {new_str}"


def format_cost_pair(old_side, new_side):
    old_cost, new_cost = old_side.get("cost_usd"), new_side.get("cost_usd")
    old_str, new_str = format_cost(old_cost), format_cost(new_cost)
    if old_cost is not None and new_cost is not None:
        delta = new_cost - old_cost
        sign = "+" if delta >= 0 else "-"
        return f"{old_str} \u2192 {new_str} ({sign}${abs(delta):,.4f})"
    return f"{old_str} \u2192 {new_str}"


def render_comparative_markdown(data):
    """Comparative report: structural/qualitative diff (delegated to
    diff_reviews.py's own renderer) followed by one wide cost/judgment
    table, old vs. new side by side per model, instead of two separate
    tables a reader would have to line up by hand."""
    old_name = data.get("old_skill_name", "unknown-old")
    new_name = data.get("new_skill_name", "unknown-new")
    runs = data.get("runs", [])

    lines = [f"# skill-eval Comparative Report: {old_name} \u2192 {new_name}", ""]

    fixture_note = render_fixture_note(data)
    if fixture_note:
        lines.append(fixture_note)

    structural_diff = data.get("structural_diff")
    if structural_diff:
        lines.append(dr.render_markdown(structural_diff, heading_level="##"))
    qualitative_diff = data.get("qualitative_diff")
    if qualitative_diff:
        lines.append(dr.render_markdown(qualitative_diff, heading_level="##"))

    lines.append("## Cost & Behavior Comparison")
    lines.append("")

    if not runs:
        lines.append("No runs recorded.")
        return "\n".join(lines) + "\n"

    lines.append("| Model Used | Tokens (old \u2192 new) | Cost (old \u2192 new) | Time (old \u2192 new) | Old Judgment | New Judgment |")
    lines.append("|---|---:|---:|---:|---|---|")
    old_costs, new_costs = [], []
    for run in runs:
        model = esc(run.get("model", "?"))
        old_side, new_side = run.get("old") or {}, run.get("new") or {}
        tokens = format_tokens_pair(old_side, new_side)
        cost_pair = format_cost_pair(old_side, new_side)
        time_pair = format_time_pair(old_side, new_side)
        old_judgment = format_judgment(old_side.get("judgment"))
        new_judgment = format_judgment(new_side.get("judgment"))
        lines.append(f"| {model} | {tokens} | {cost_pair} | {time_pair} | {old_judgment} | {new_judgment} |")
        old_costs.append(old_side.get("cost_usd"))
        new_costs.append(new_side.get("cost_usd"))

    total_old, total_new = sum_costs(old_costs), sum_costs(new_costs)
    if total_old is not None or total_new is not None:
        lines.append("")
        delta_note = ""
        if total_old is not None and total_new is not None:
            delta = total_new - total_old
            sign = "+" if delta >= 0 else "-"
            delta_note = f" ({sign}${abs(delta):,.4f})"
        lines.append(f"Total cost: {format_cost(total_old)} \u2192 {format_cost(total_new)}{delta_note}")

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

    if data.get("report_type") == "comparative":
        report = render_comparative_markdown(data)
    else:
        report = render_markdown(data)

    if out_path:
        Path(out_path).write_text(report, encoding="utf-8")
        print(f"Wrote {out_path}")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
