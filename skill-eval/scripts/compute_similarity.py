#!/usr/bin/env python3
"""
compute_similarity.py - how close is each model's produced output to the
verified output? Markdown in, Markdown out; no model, no Claude session.

Usage:
    python compute_similarity.py <skill_dir> [--profile <name>] [--out <path>]

Reads from <skill_dir>:
    evals/verified-outputs/<case>                       one verified output per case
    evals/<skill>_<version>_outputs/<model>/run_<r>/<case>
                                                        produced outputs (written by run_skill.py);
                                                        a case with no output scores 0 and is "missing"
    config.yaml                                         similarity profiles and the stability limits
                                                        (min_valid_runs, max_case_spread_points)

Writes <skill_dir>/step_reports/05_similarity.md unless --out is given: per model the score (mean over
complete runs), run spread and stability, per run and per case tables, and flags.

Similarity (0-100%) scores an OUTPUT against the verified output. It is not a
score for the skill. For the "document" profile it is a weighted mix of:
    fact recall      concrete facts of the verified output (numbers, units, backticked
                     identifiers) found in the produced output
    content overlap  unigram + bigram F1 between the two texts
    structure        required sections present, and item count close to the verified one
"""

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_final_report import load_config, skill_meta  # noqa: E402
from profiles import get_profile  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

# ---------- reading runs ----------

def read_cases(verified_dir, pattern="*"):
    """{file name: text} of the verified outputs the profile accepts (its verified_glob)."""
    return {f.name: f.read_text(encoding="utf-8") for f in sorted(Path(verified_dir).glob(pattern)) if f.is_file()}


def _run_number(path):
    suffix = path.name[len("run_"):]
    return int(suffix) if suffix.isdigit() else None


def read_runs(out_dir, cases):
    """{model: {run: {case: produced text | None}}} from <model>/run_<r>/<case>.

    A case is None (missing) when its output file is absent or empty, or its <case>.json says it failed.
    """
    out = {}
    for model_dir in sorted(p for p in Path(out_dir).glob("*") if p.is_dir()):
        runs = {}
        for run_dir in sorted(model_dir.glob("run_*"), key=lambda p: _run_number(p) or 0):
            r = _run_number(run_dir)
            if r is None:
                continue
            runs[r] = {}
            for case in cases:
                text = None
                f, meta = run_dir / case, run_dir / f"{case}.json"
                if f.is_file() and f.read_text(encoding="utf-8").strip():
                    text = f.read_text(encoding="utf-8")
                    if meta.is_file():
                        try:
                            if json.loads(meta.read_text(encoding="utf-8")).get("status") != "ok":
                                text = None
                        except ValueError:
                            pass
                runs[r][case] = text
        if runs:
            out[model_dir.name] = runs
    return out


# ---------- scoring ----------

def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def spread(values):
    return max(values) - min(values) if len(values) >= 2 else None


def analyze_model(per_run, cases, stability, components=("fact_recall", "content_overlap", "structure")):
    """Score, run spread and stability of one model. Pure function.

    per_run: {run: {case: result from score_case}}. A run is complete when no case has no_output.
    Score = mean over complete runs of the run score (mean of the cases). Stability is judged on the
    spread of one case over the complete runs, never between different cases.
    Status: insufficient (too few complete runs: an infrastructure problem), single run, stable, unstable.
    """
    runs = []
    for r, by_case in sorted(per_run.items()):
        results = [by_case[c] for c in cases]
        runs.append({"run": r, "score": mean(x["similarity"] for x in results),
                     "missing_cases": sum(1 for x in results if x["no_output"]),
                     "valid": not any(x["no_output"] for x in results), "results": by_case})
    valid = [x for x in runs if x["valid"]]
    required = min(int(stability["min_valid_runs"]), len(runs))
    case_spreads = {c: spread([x["results"][c]["similarity"] for x in valid]) for c in cases}
    mean_case_spread = mean(case_spreads.values())
    if len(valid) < required or not valid:
        status = "insufficient"
    elif len(valid) < 2:
        status = "single run"
    else:
        status = "unstable" if mean_case_spread > float(stability["max_case_spread_points"]) else "stable"
    ordered = sorted(valid, key=lambda x: x["score"])
    return {
        "runs": runs, "valid_runs": len(valid), "status": status,
        "score": mean(x["score"] for x in valid), "all_runs_score": mean(x["score"] for x in runs),
        "parts": {k: mean(mean(x["results"][c][k] for c in cases) for x in valid) for k in components},
        "run_spread": spread([x["score"] for x in valid]), "case_spreads": case_spreads,
        "mean_case_spread": mean_case_spread,
        "median_run": ordered[(len(ordered) - 1) // 2]["run"] if ordered else None,
    }


def skill_flags(analyses, cases, stability):
    """Lines for the report's flag section. Pure function."""
    flags = []
    unstable = [m for m, a in analyses.items() if a["status"] == "unstable"]
    if len(unstable) >= 2:
        flags.append(f"**Skill flag:** unstable results on {len(unstable)} models ({', '.join(unstable)}). "
                     "Check the transcripts (`.jsonl` files): was the skill loaded, were its steps followed? "
                     "The skill may not be read as a clear instruction.")
    elif len(unstable) == 1:
        flags.append(f"**Model note:** `{unstable[0]}` is unstable while the other models are not. "
                     "This points to a limit of that model, not of the skill.")
    insufficient = [m for m, a in analyses.items() if a["status"] == "insufficient"]
    if insufficient:
        flags.append(f"**Run problem:** too few complete runs for {', '.join(insufficient)}. This is an infrastructure "
                     "problem (timeouts, budget, errors), not instability. See `run_on_<model>_report.md` and the `.json` files.")
    low = float(stability.get("low_case_points", 60))
    for c in cases:
        best = max([x["results"][c]["similarity"] for a in analyses.values() for x in a["runs"] if x["valid"]] or [None],
                   key=lambda v: -1 if v is None else v)
        if best is not None and best < low:
            flags.append(f"**Check the verified output or the metric:** `{c}` stays low in every complete run of every "
                         f"model (best {best:.1f}%).")
    return flags


def score_all(skill_dir, profile, stability):
    meta = skill_meta(skill_dir)
    verified = read_cases(Path(skill_dir) / "evals" / "verified-outputs", profile.verified_glob)
    if not verified:
        sys.exit(f"Error: no verified outputs matching {profile.verified_glob} in {skill_dir}/evals/verified-outputs/")
    out_dir = Path(skill_dir) / "evals" / f"{meta['name']}_{meta['version']}_outputs"
    produced = read_runs(out_dir, list(verified))
    if not produced:
        sys.exit(f"Error: no runs in {out_dir}. Run scripts/run_skill.py first.")
    cases = list(verified)
    results = {model: {r: {c: profile.score(verified[c], texts[c]) for c in cases} for r, texts in runs.items()}
               for model, runs in produced.items()}
    analyses = {model: analyze_model(per_run, cases, stability, [k for k, _ in profile.components])
                for model, per_run in results.items()}
    return meta, cases, analyses


def pct(x):
    return "unavailable" if x is None else f"{x:.1f}%"


def pts(x):
    return "n/a" if x is None else f"{x:.1f}"


def render(meta, cases, analyses, profile, stability):
    sentence, bullets = profile.report_intro()
    labels = [label for _, label in profile.components]
    keys = [key for key, _ in profile.components]
    out = [f"# Similarity to verified outputs: {meta['name']} {meta['version']}", "",
           f"Profile: `{profile.name}`. {sentence} It scores the produced output against the verified output; "
           "it is not a score for the skill.", ""]
    out += [f"- {b}" for b in bullets]
    out += ["- **Missing case:** no output (failed or cut-off run) scores 0 and makes the run incomplete.",
            f"- **Model score:** mean over the complete runs. **Case spread:** highest minus lowest similarity of one case "
            f"over the complete runs. A model is `unstable` when the mean case spread is above "
            f"{float(stability['max_case_spread_points']):g} points, and `insufficient` with fewer than "
            f"{int(stability['min_valid_runs'])} complete runs.", "",
            "## Per model", "",
            "| Model | Similarity | " + " | ".join(labels) + " | Runs | Complete runs | Run spread "
            "| Case spread | Stability | All runs, missing = 0 | Median run |",
            "| --- | ---: | " + " | ".join("---:" for _ in labels) + " | ---: | ---: | ---: | ---: | --- | ---: | ---: |"]
    for model, a in analyses.items():
        p = a["parts"]
        out.append(f"| {model} | {pct(a['score'])} | " + " | ".join(pct(p[k]) for k in keys)
                   + f" | {len(a['runs'])} | {a['valid_runs']} | {pts(a['run_spread'])} "
                   f"| {pts(a['mean_case_spread'])} | {a['status']} | {pct(a['all_runs_score'])} "
                   f"| {a['median_run'] if a['median_run'] is not None else 'n/a'} |")
    out += ["", "## Per run", "", "| Model | Run | Similarity | Status | Missing cases |", "| --- | ---: | ---: | --- | ---: |"]
    for model, a in analyses.items():
        for x in a["runs"]:
            out.append(f"| {model} | {x['run']} | {pct(x['score'])} | {'complete' if x['valid'] else 'incomplete'} "
                       f"| {x['missing_cases']} |")
    out += ["", "## Per case", "", "Means over the complete runs.", "",
            "| Case | Model | Similarity | " + " | ".join(labels) + " | Spread |",
            "| --- | --- | ---: | " + " | ".join("---:" for _ in labels) + " | ---: |"]
    for case in cases:
        for model, a in analyses.items():
            valid = [x["results"][case] for x in a["runs"] if x["valid"]]
            if not valid:
                out.append(f"| {case} | {model} | unavailable | " + " | ".join("unavailable" for _ in labels) + " | n/a |")
                continue
            out.append(f"| {case} | {model} | {pct(mean(r['similarity'] for r in valid))} | "
                       + " | ".join(pct(mean(r[k] for r in valid)) for k in keys) + f" | {pts(a['case_spreads'][case])} |")
    out += ["", "## Flags", ""]
    flags = skill_flags(analyses, cases, stability)
    out += [f"- {f}" for f in flags] or ["_None._"]
    out += ["", "## Facts not found in the produced output", "", "Taken from the median run of each model.", ""]
    any_missing = False
    for case in cases:
        for model, a in analyses.items():
            run = next((x for x in a["runs"] if x["run"] == a["median_run"]), None)
            r = run["results"][case] if run else None
            if r and r["missing"]:
                any_missing = True
                shown = ", ".join(f"`{m}`" for m in r["missing"][:12])
                more = f" (+{len(r['missing']) - 12} more)" if len(r["missing"]) > 12 else ""
                out.append(f"- {case} / {model} (run {run['run']}): {len(r['missing'])} of {r['n_facts']} facts: {shown}{more}")
    if not any_missing:
        out.append("_None._")
    out += ["", "A fact listed here may still be present in other words. Read it together with the comparison "
            "notes in `04_comparison_<model>_a.md` and `_b.md`."]
    return "\n".join(out) + "\n"


def load_stability():
    cfg = load_config()
    return {"max_case_spread_points": 10, "min_valid_runs": 2, "low_case_points": 60, **(cfg.get("stability") or {})}


def main():
    args = sys.argv[1:]

    def opt(name):
        if name in args:
            i = args.index(name)
            if i + 1 >= len(args):
                sys.exit(f"Error: {name} needs a value.")
            return args[i + 1]

    if not args or args[0].startswith("--"):
        sys.exit("Usage: python compute_similarity.py <skill_dir> [--profile <name>] [--out <path>]")
    skill_dir = args[0]
    if not (Path(skill_dir) / "SKILL.md").is_file():
        sys.exit(f"Error: no SKILL.md in {skill_dir}")
    profile = get_profile(opt("--profile"))
    ok, note = profile.check_applicable(skill_dir)
    if not ok:
        sys.exit(f"Error: profile '{profile.name}' cannot judge this skill: {note}")
    stability = load_stability()
    meta, cases, analyses = score_all(skill_dir, profile, stability)
    out_path = Path(opt("--out") or Path(skill_dir) / "step_reports" / "05_similarity.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render(meta, cases, analyses, profile, stability), encoding="utf-8")
    print(f"Wrote {out_path}")
    for model, a in analyses.items():
        print(f"  {model}: {pct(a['score'])} ({a['status']}, {a['valid_runs']}/{len(a['runs'])} complete runs, "
              f"median run {a['median_run']})")


if __name__ == "__main__":
    main()
