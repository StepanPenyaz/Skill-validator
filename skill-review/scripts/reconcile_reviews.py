#!/usr/bin/env python3
"""
reconcile_reviews.py — deterministic aggregation over N independent
qualitative review runs of the SAME skill (see SKILL.md's "Self-consistency"
section and references/schema.md).

This does NOT run the qualitative pass itself — that's Claude reading the
skill against references/rubric.md and following SKILL.md Steps 1-5, once
per independent run, each written to its own
<skill-name>-review-run<N>.json. This script only reconciles those
already-produced JSON files into a single consensus view: which findings
and category scores are stable across runs (real signal) versus which only
showed up once (plausible sampling noise from a single LLM pass).

Usage:
    python3 reconcile_reviews.py <run1.json> <run2.json> [<runN.json> ...] \
        [--threshold N] [--out <path>]

--threshold sets how many runs must agree for a finding to be "confirmed"
(default: a simple majority, floor(runs/2) + 1).

Prints one JSON object (the consensus report) to stdout, or writes it to
--out if given. Every input file must be a <skill-name>-review.json per
references/schema.md, all for the same skill_name.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

CATEGORY_SEVERITY_RANK = {"pass": 0, "minor": 1, "major": 2, "blocker": 3}


def fail(msg):
    print(json.dumps({"fatal_error": msg}))
    sys.exit(1)


def load_run(path):
    p = Path(path)
    if not p.is_file():
        fail(f"Not a file: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"Invalid JSON in {p}: {e}")
    for required in ("skill_name", "overall_verdict", "category_scores", "findings"):
        if required not in data:
            fail(f"{p} is missing required field '{required}' — is this a <skill-name>-review.json?")
    return data


def consensus_value(values, rank=None):
    """Majority element of `values`; ties broken toward the higher-ranked value
    (per `rank`, if given) rather than arbitrarily — e.g. a 1-1 split between
    'pass' and 'blocker' resolves to 'blocker', since understating risk on a
    tie is worse than overstating it."""
    counts = Counter(values)
    max_count = max(counts.values())
    candidates = [v for v, c in counts.items() if c == max_count]
    if len(candidates) == 1:
        return candidates[0]
    if rank:
        return max(candidates, key=lambda v: rank.get(v, -1))
    return sorted(candidates)[0]


def compute_overall_verdict(category_scores):
    """Mirrors references/schema.md's stated derivation rule, so a
    reconciled report's overall_verdict is computed the same way a single
    run's is — not a separate, drifting definition."""
    values = set(category_scores.values())
    if "blocker" in values:
        return "blocked"
    if "major" in values:
        return "needs_work"
    if "minor" in values:
        return "pass_with_suggestions"
    return "pass"


def finding_key(finding):
    """Groups findings across independent runs by (category, location) —
    location is usually a concrete, stable pointer (a file:line, a
    frontmatter field) even when two runs phrase the same issue
    differently, so it's a more reliable match key than free text. A
    finding with no location can't be reliably matched to another run's,
    so it's kept as its own singleton group rather than guessed at."""
    category = finding.get("category")
    location = finding.get("location")
    if location:
        return (category, location)
    return (category, f"__no_location__:{id(finding)}")


def reconcile(runs, threshold):
    skill_names = {r["skill_name"] for r in runs}
    if len(skill_names) > 1:
        fail(f"Input files reference different skills: {sorted(skill_names)}. "
             "Reconciliation only makes sense across runs of the SAME skill.")
    skill_name = skill_names.pop()

    # --- Category scores: majority per category, ties toward more severe ---
    all_categories = set()
    for r in runs:
        all_categories.update(r["category_scores"].keys())
    category_scores = {}
    category_scores_by_run = [r["category_scores"] for r in runs]
    for category in sorted(all_categories):
        values = [r["category_scores"].get(category) for r in runs if category in r["category_scores"]]
        category_scores[category] = consensus_value(values, CATEGORY_SEVERITY_RANK)
    overall_verdict = compute_overall_verdict(category_scores)
    overall_verdict_by_run = [r["overall_verdict"] for r in runs]

    # --- Findings: group by (category, location) across all runs ---
    groups = defaultdict(list)  # key -> [(run_index, finding), ...]
    for run_index, r in enumerate(runs):
        for f in r["findings"]:
            groups[finding_key(f)].append((run_index, f))

    findings = []
    for (category, location), entries in groups.items():
        run_indices = sorted({idx for idx, _ in entries})
        agreement_count = len(run_indices)
        severities = [f["severity"] for _, f in entries]
        consensus_severity = consensus_value(severities, CATEGORY_SEVERITY_RANK
                                              if set(severities) <= set(CATEGORY_SEVERITY_RANK) else None)
        # Prefer a representative finding whose own severity matches the
        # consensus severity, so the example text lines up with the verdict
        # being reported — falls back to the first report if none match
        # (can happen when every run disagreed on severity).
        representative = next((f for _, f in entries if f["severity"] == consensus_severity), entries[0][1])
        variant_issue_texts = sorted({f["issue"] for _, f in entries if f["issue"] != representative["issue"]})

        findings.append({
            "category": category,
            "location": location,
            "agreement_count": agreement_count,
            "agreement_fraction": round(agreement_count / len(runs), 4),
            "confirmed": agreement_count >= threshold,
            "consensus_severity": consensus_severity,
            "severities_by_run": [
                next((f["severity"] for idx, f in entries if idx == i), None) for i in range(len(runs))
            ],
            "representative_issue": representative["issue"],
            "representative_suggested_rewrite": representative.get("suggested_rewrite"),
            "representative_why_it_matters": representative.get("why_it_matters"),
            "variant_issue_texts": variant_issue_texts,
        })

    # Confirmed first, then by agreement (desc), then category/location for a stable order.
    findings.sort(key=lambda f: (not f["confirmed"], -f["agreement_count"], f["category"], f["location"]))

    confirmed_count = sum(1 for f in findings if f["confirmed"])
    unconfirmed_count = len(findings) - confirmed_count

    return {
        "skill_name": skill_name,
        "runs": len(runs),
        "threshold": threshold,
        "overall_verdict": overall_verdict,
        "overall_verdict_by_run": overall_verdict_by_run,
        "category_scores": category_scores,
        "category_scores_by_run": category_scores_by_run,
        "findings": findings,
        "confirmed_findings_count": confirmed_count,
        "unconfirmed_findings_count": unconfirmed_count,
        "summary": (
            f"{confirmed_count} of {len(findings)} candidate finding(s) confirmed "
            f"(reported in at least {threshold} of {len(runs)} independent runs); "
            f"{unconfirmed_count} appeared in only a minority of runs and are more likely "
            "sampling noise than a stable signal — review those individually before acting on them."
        ),
    }


def main():
    args = sys.argv[1:]
    threshold_override = None
    out_path = None

    if "--threshold" in args:
        idx = args.index("--threshold")
        if idx + 1 >= len(args):
            fail("--threshold requires an integer argument.")
        try:
            threshold_override = int(args[idx + 1])
        except ValueError:
            fail(f"--threshold value must be an integer, got '{args[idx + 1]}'.")
        del args[idx:idx + 2]

    if "--out" in args:
        idx = args.index("--out")
        if idx + 1 >= len(args):
            fail("--out requires a path argument.")
        out_path = args[idx + 1]
        del args[idx:idx + 2]

    if len(args) < 2:
        fail(
            "Usage: python reconcile_reviews.py <run1.json> <run2.json> [<runN.json> ...] "
            "[--threshold N] [--out <path>] — need at least 2 independent review runs to reconcile."
        )

    runs = [load_run(p) for p in args]
    threshold = threshold_override if threshold_override is not None else (len(runs) // 2) + 1
    if threshold < 1 or threshold > len(runs):
        fail(f"--threshold must be between 1 and {len(runs)} (number of runs given), got {threshold}.")

    result = reconcile(runs, threshold)
    output = json.dumps(result, indent=2)

    if out_path:
        Path(out_path).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
