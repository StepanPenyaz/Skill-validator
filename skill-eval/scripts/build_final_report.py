#!/usr/bin/env python3
"""
build_final_report.py - assembles a skill's final_report.md from Markdown
step reports. Markdown in, Markdown out; no JSON, no model, no Claude session.

Usage:
    python build_final_report.py <skill_dir> [--baseline <older_skill_dir>] [--out <path>]

Reads from <skill_dir>:
    SKILL.md                                      name, version, description (frontmatter)
    step_reports/01_structure.md                  structure check report
    step_reports/02_rubric.md                     rubric review report
    step_reports/04_comparison_<model>.md         table ROWS only, one per model:
                                                  | verified | produced | model | version | notes |
                                                  plus an optional line
                                                  "Verdict: Equivalent | Minor gaps | Major gaps - reason"
    step_reports/05_similarity.md                 output of compute_similarity.py (optional)
    evals/<skill>_<version>_outputs/run_on_<model>_report.md
                                                  lines like "- Tokens used: 35120",
                                                  "- Time spent: 5m 12s", "- Total cost: $0.2107"

Writes <skill_dir>/final_report.md unless --out is given. Sections are
numbered from 1. Section 8 is the model recommendation: a deterministic rule
over similarity, verdict, tokens, time and cost (see recommend()).

With --baseline, <older_skill_dir> must already contain a final_report.md
(produced by this script). Its tables are parsed and shown next to the
current ones with V1 / V2 / delta columns, and the summary gets three
Mermaid charts (token usage, total cost, time spent).
"""

import re
import sys
from pathlib import Path

import yaml

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

RUN_HEADER = "| Model used | Number of tokens used | Time spent | Total cost |"
COMPARE_HEADER = "| Verified output | Produced output | Model | Skill version | Notes |"
SIM_SUMMARY_HEADER = "| Model | Similarity"
SIM_CASE_HEADER = "| Case | Model | Similarity"
REC_HEADER = "| Model | Similarity | Quality verdict | Tokens | Time | Cost | Similarity points per $ |"
MODELS_CONFIG = Path(__file__).resolve().parent.parent / "references" / "models_config.yaml"
DEFAULT_TOLERANCE = 3.0
VERDICTS = {"equivalent": 0, "minor gaps": 1, "major gaps": 2}


# ---------- small helpers ----------

def read(path):
    p = Path(path)
    return p.read_text(encoding="utf-8").strip() if p.is_file() else None


def demote(text, levels=2):
    """Push Markdown headings down so an embedded report sits under a section heading."""
    out, in_fence = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("#"):
            line = "#" * levels + line
        out.append(line)
    return "\n".join(out)


def skill_meta(skill_dir):
    text = (Path(skill_dir) / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    fm = yaml.safe_load(m.group(1)) if m else {}
    meta = fm.get("metadata") or {}
    return {
        "name": str(fm.get("name") or Path(skill_dir).resolve().name),
        "version": str(meta.get("version") or "unknown"),
        "description": " ".join(str(fm.get("description") or "").split()),
    }


def fmt_tokens(n):
    return "unavailable" if n is None else f"{n:,}"


def fmt_time(s):
    if s is None:
        return "unavailable"
    s = int(round(s))
    return f"{s // 60}m {s % 60:02d}s" if s >= 60 else f"{s}s"


def fmt_cost(c):
    return "unavailable" if c is None else f"${c:,.4f}"


def parse_tokens(t):
    t = t.strip().replace(",", "")
    return int(t) if t.isdigit() else None


def parse_time(t):
    m = re.fullmatch(r"\s*(?:(\d+)m\s*)?(\d+)s\s*", t)
    return int(m.group(1) or 0) * 60 + int(m.group(2)) if m else None


def parse_cost(t):
    try:
        return float(t.strip().lstrip("$").replace(",", ""))
    except ValueError:
        return None


def parse_pct(t):
    try:
        return float(t.strip().rstrip("%"))
    except ValueError:
        return None


def fmt_pct(p):
    return "unavailable" if p is None else f"{p:.1f}%"


def delta(old, new, fmt, signed_fmt=None):
    if old is None or new is None:
        return "n/a"
    d = new - old
    sign = "+" if d > 0 else ("-" if d < 0 else "")
    pct = f" ({sign}{abs(d) / old * 100:.0f}%)" if old else ""
    return f"{sign}{fmt(abs(d))}{pct}"


# ---------- reading run reports ----------

def read_runs(skill_dir, meta):
    out_dir = Path(skill_dir) / "evals" / f"{meta['name']}_{meta['version']}_outputs"
    runs = {}
    for f in sorted(out_dir.glob("run_on_*_report.md")):
        fields = dict(re.findall(r"^-\s*([^:]+):\s*(.+?)\s*$", f.read_text(encoding="utf-8"), re.M))
        model = fields.get("Model name") or f.stem[len("run_on_"):-len("_report")]
        runs[model] = {
            "tokens": parse_tokens(fields.get("Tokens used", "")),
            "time": parse_time(fields.get("Time spent", "")),
            "cost": parse_cost(fields.get("Total cost", "")),
        }
    return runs


def read_comparison_rows(skill_dir):
    rows = []
    for f in sorted((Path(skill_dir) / "step_reports").glob("04_comparison_*.md")):
        rows += [l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip().startswith("|")]
    return rows


VERDICT_LINE = re.compile(r"^\W*Verdict:\s*(Equivalent|Minor gaps|Major gaps)\b\s*[-:–—]?\s*(.*)$",
                          re.M | re.I)


def read_verdicts(skill_dir):
    """The 'Verdict: <Equivalent|Minor gaps|Major gaps> - reason' line of each 04_comparison_<model>.md."""
    out = {}
    for f in sorted((Path(skill_dir) / "step_reports").glob("04_comparison_*.md")):
        m = VERDICT_LINE.search(f.read_text(encoding="utf-8"))
        if m:
            out[f.stem[len("04_comparison_"):]] = (m.group(1).lower(), m.group(2).strip())
    return out


def read_similarity(skill_dir):
    """Per-model averages and per-case rows from step_reports/05_similarity.md (None if not run)."""
    text = read(Path(skill_dir) / "step_reports" / "05_similarity.md")
    if text is None:
        return None
    summary = {cells[0]: parse_pct(cells[1]) for cells in table_rows(text, SIM_SUMMARY_HEADER)}
    return {"summary": summary, "cases": table_rows(text, SIM_CASE_HEADER)}


def read_tolerance():
    try:
        cfg = yaml.safe_load(MODELS_CONFIG.read_text(encoding="utf-8")) or {}
        return float((cfg.get("recommendation") or {}).get("tolerance_points", DEFAULT_TOLERANCE))
    except (OSError, ValueError, yaml.YAMLError):
        return DEFAULT_TOLERANCE


def split_cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


# ---------- reading a baseline final_report.md ----------

def sections_of(report_text):
    parts = re.split(r"^## (\d+)\. .*$", report_text, flags=re.M)
    return {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}


def table_rows(section_text, header_start):
    rows, on = [], False
    for line in section_text.splitlines():
        if line.startswith(header_start):
            on = True
            continue
        if on:
            if not line.startswith("|"):
                break
            if not set(line.replace("|", "").strip()) <= set("-: "):
                rows.append(split_cells(line))
    return rows


def read_baseline(base_dir):
    text = read(Path(base_dir) / "final_report.md")
    if text is None:
        sys.exit(f"Error: {base_dir}/final_report.md not found. Run skill-eval on the older version first.")
    sec = sections_of(text)
    runs = {}
    for cells in table_rows(sec.get(4, ""), "| Model used"):
        runs[cells[0]] = {"tokens": parse_tokens(cells[1]), "time": parse_time(cells[2]), "cost": parse_cost(cells[3])}
    m = re.search(r"Version:\s*`([^`]+)`", sec.get(2, ""))
    return {
        "version": m.group(1) if m else "unknown",
        "runs": runs,
        "similarity": {c[0].replace(" (recommended)", ""): parse_pct(c[1]) for c in table_rows(sec.get(8, ""), SIM_SUMMARY_HEADER) if len(c) >= 2},
        "comparison": table_rows(sec.get(5, ""), "| Verified output"),
        "structure": sec.get(6, ""),
        "rubric": sec.get(7, ""),
    }


# ---------- rendering ----------

def chart(title, unit, models, old, new, key):
    def num(v):
        return 0 if v is None else round(v, 4) if key == "cost" else round(v)
    ymax = max([num(x) for x in old + new] + [1])
    ymax = int(ymax * 1.15) + 1
    return "\n".join([
        "```mermaid", "xychart-beta",
        f'    title "{title} - V1 (first bar) vs V2 (second bar)"',
        f"    x-axis [{', '.join(models)}]",
        f'    y-axis "{unit}" 0 --> {ymax}',
        f"    bar [{', '.join(str(num(x)) for x in old)}]",
        f"    bar [{', '.join(str(num(x)) for x in new)}]",
        "```",
    ])


def run_table(runs):
    lines = [RUN_HEADER, "| --- | ---: | ---: | ---: |"]
    for m, r in runs.items():
        lines.append(f"| {m} | {fmt_tokens(r['tokens'])} | {fmt_time(r['time'])} | {fmt_cost(r['cost'])} |")
    return lines


def compare_run_table(old_runs, new_runs, v1, v2):
    lines = [
        f"| Model | Tokens V1 ({v1}) | Tokens V2 ({v2}) | Tokens change | Time V1 | Time V2 | Time change "
        "| Cost V1 | Cost V2 | Cost change |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for m in new_runs:
        o, n = old_runs.get(m, {}), new_runs[m]
        ot, nt = o.get("tokens"), n["tokens"]
        os_, ns = o.get("time"), n["time"]
        oc, nc = o.get("cost"), n["cost"]
        lines.append(
            f"| {m} | {fmt_tokens(ot)} | {fmt_tokens(nt)} | {delta(ot, nt, lambda x: f'{x:,}')} "
            f"| {fmt_time(os_)} | {fmt_time(ns)} | {delta(os_, ns, fmt_time)} "
            f"| {fmt_cost(oc)} | {fmt_cost(nc)} | {delta(oc, nc, fmt_cost)} |"
        )
    return lines


def recommend(rows, tolerance):
    """Pick the model to run the skill with. Pure function, no I/O.

    rows: dicts with model, similarity (0-100 or None), verdict (None, "equivalent", "minor gaps",
    "major gaps"), tokens, time, cost. Rule:
      1. drop models with "major gaps" or without similarity or cost;
      2. candidates = models within `tolerance` points of the best remaining similarity;
      3. recommend the cheapest candidate (ties: faster, then fewer tokens, then more similar).
    """
    inf = float("inf")
    excluded, pool = [], []
    for r in rows:
        if r["similarity"] is None:
            excluded.append((r["model"], "no similarity measured"))
        elif r["cost"] is None:
            excluded.append((r["model"], "cost unavailable"))
        elif r["verdict"] == "major gaps":
            excluded.append((r["model"], "verdict: major gaps"))
        else:
            pool.append(r)
    res = {"excluded": excluded, "candidates": [], "recommended": None, "best": None}
    scored = [r for r in rows if r["similarity"] is not None]
    res["highest_quality"] = (max(scored, key=lambda r: (r["similarity"], -VERDICTS.get(r["verdict"], 1)))
                              if scored else None)
    costed = [r for r in rows if r["cost"] is not None]
    res["cheapest"] = min(costed, key=lambda r: r["cost"]) if costed else None
    timed = [r for r in rows if r["time"] is not None]
    res["fastest"] = min(timed, key=lambda r: r["time"]) if timed else None
    if pool:
        res["best"] = max(pool, key=lambda r: r["similarity"])
        res["candidates"] = [r for r in pool if r["similarity"] >= res["best"]["similarity"] - tolerance]
        res["recommended"] = min(res["candidates"], key=lambda r: (
            r["cost"], r["time"] if r["time"] is not None else inf,
            r["tokens"] if r["tokens"] is not None else inf, -r["similarity"]))
    return res


def ratio_text(a, b, what):
    """'N.N times <what>' for a / b, or '' when it cannot be computed."""
    return f"{a / b:.1f} times {what}" if a and b else ""


def recommendation_rows(runs, sim, verdicts):
    rows = []
    for m, r in runs.items():
        v = verdicts.get(m)
        rows.append({"model": m, "similarity": ((sim or {}).get("summary") or {}).get(m),
                     "verdict": v[0] if v else None, "verdict_reason": v[1] if v else "",
                     "tokens": r["tokens"], "time": r["time"], "cost": r["cost"]})
    return rows


def render_recommendation(rows, tolerance, sim, base):
    out = ["## 8. Model recommendation", ""]
    if sim is None:
        out += ["_No similarity data. Run `python skill-eval/scripts/compute_similarity.py <skill_dir>` "
                "(step 4b) and build the report again._", ""]
        return out
    res = recommend(rows, tolerance)
    rec = res["recommended"]
    if rec is None:
        out += ["**No model can be recommended:** every model is excluded or has missing data (see below).", ""]
    else:
        best = res["best"]
        names = ", ".join(f"`{r['model']}`" for r in res["candidates"])
        if len(res["candidates"]) == 1 and rec is best:
            why = (f"it has the highest similarity to the verified outputs and no other model is "
                   f"within {tolerance:g} points of it.")
        else:
            why = (f"it is within {tolerance:g} points of the most similar model (`{best['model']}`, "
                   f"{fmt_pct(best['similarity'])}) and is the cheapest of the candidates ({names}).")
        out += [f"**Recommended model: `{rec['model']}`.** {fmt_pct(rec['similarity'])} similar to the verified "
                f"outputs, {fmt_tokens(rec['tokens'])} tokens, {fmt_time(rec['time'])}, {fmt_cost(rec['cost'])} "
                f"for all inputs. Chosen because {why}", ""]
    if not any(r["verdict"] for r in rows):
        out += ["_No `Verdict:` line was found in the comparison reports, so no model was dropped for quality gaps._",
                ""]

    out += [REC_HEADER, "| --- | ---: | --- | ---: | ---: | ---: | ---: |"]
    for r in rows:
        per_dollar = (f"{r['similarity'] / r['cost']:.1f}"
                      if r["similarity"] is not None and r["cost"] else "unavailable")
        verdict = r["verdict"].capitalize() if r["verdict"] else "not given"
        mark = " (recommended)" if rec is not None and r["model"] == rec["model"] else ""
        out.append(f"| {r['model']}{mark} | {fmt_pct(r['similarity'])} | {verdict} | {fmt_tokens(r['tokens'])} "
                   f"| {fmt_time(r['time'])} | {fmt_cost(r['cost'])} | {per_dollar} |")
    out.append("")

    out += ["### 8.1 At a glance", ""]
    for label, key, shown in (("Highest similarity", "highest_quality", lambda r: fmt_pct(r["similarity"])),
                              ("Cheapest", "cheapest", lambda r: fmt_cost(r["cost"])),
                              ("Fastest", "fastest", lambda r: fmt_time(r["time"]))):
        r = res[key]
        out.append(f"- {label}: `{r['model']}` ({shown(r)})" if r else f"- {label}: unavailable")
    hq = res["highest_quality"]
    if rec and hq and hq["model"] != rec["model"]:
        extra = [x for x in (ratio_text(hq["cost"], rec["cost"], "the cost"),
                             ratio_text(hq["time"], rec["time"], "the time")) if x]
        out.append(f"- Trade-off: `{hq['model']}` is {hq['similarity'] - rec['similarity']:.1f} points more "
                   f"similar than `{rec['model']}`" + (" but needs " + " and ".join(extra) if extra else "") + ".")
    elif rec and hq:
        out.append(f"- Trade-off: none. `{rec['model']}` is both the most similar and the cheapest candidate.")
    ch = res["cheapest"]
    if rec and ch and ch["model"] != rec["model"] and ch["similarity"] is not None:
        share = f" ({ch['cost'] / rec['cost'] * 100:.0f}% of the cost)" if rec["cost"] else ""
        out.append(f"- Cheaper option: `{ch['model']}`{share} but {rec['similarity'] - ch['similarity']:.1f} points "
                   f"less similar than `{rec['model']}`.")
    out.append("")
    if res["excluded"]:
        out += ["Not considered: " + "; ".join(f"`{m}` ({why})" for m, why in res["excluded"]) + ".", ""]
    reasons = [f"- `{r['model']}`: {r['verdict_reason']}" for r in rows if r["verdict_reason"]]
    if reasons:
        out += ["Verdicts from the comparison step:", ""] + reasons + [""]

    out += ["### 8.2 How the choice is made", "",
            "1. Drop models with a `Major gaps` verdict (a requirement missing or contradicted) and models "
            "with no similarity or cost.",
            f"2. Candidates are the models within {tolerance:g} points of the best similarity "
            "(`recommendation.tolerance_points` in `references/models_config.yaml`).",
            "3. Recommend the cheapest candidate. Ties: faster, then fewer tokens.", ""]
    if base and base.get("similarity"):
        out += ["### 8.3 Similarity: V1 and V2", "", "| Model | Similarity V1 | Similarity V2 | Change (points) |",
                "| --- | ---: | ---: | ---: |"]
        for r in rows:
            o, n = base["similarity"].get(r["model"]), r["similarity"]
            chg = "n/a" if o is None or n is None else f"{n - o:+.1f}"
            out.append(f"| {r['model']} | {fmt_pct(o)} | {fmt_pct(n)} | {chg} |")
        out.append("")
    n_cases = len({c[0] for c in sim["cases"]})
    out += ["### Caveats", "",
            f"- Similarity is a proxy measured on {n_cases} case(s). It checks facts, wording and structure against "
            "the verified output. It does not replace reading the comparison notes in section 5.",
            "- Cost is estimated from the harness token total and a blended price, so small cost differences are noise.",
            "- With few cases, a difference of a point or two in similarity is inside the noise.", ""]
    return out


def counts_line(text):
    m = re.search(r"(\d+) blocker\(s\), (\d+) warning\(s\), (\d+) info", text or "")
    return tuple(int(x) for x in m.groups()) if m else None


def build(skill_dir, baseline_dir=None):
    meta = skill_meta(skill_dir)
    steps = Path(skill_dir) / "step_reports"
    structure = read(steps / "01_structure.md") or "_Not run._"
    rubric = read(steps / "02_rubric.md") or "_Not run._"
    runs = read_runs(skill_dir, meta)
    cmp_rows = read_comparison_rows(skill_dir)
    sim = read_similarity(skill_dir)
    rec_rows = recommendation_rows(runs, sim, read_verdicts(skill_dir))
    tolerance = read_tolerance()
    base = read_baseline(baseline_dir) if baseline_dir else None
    v1, v2 = (base["version"] if base else None), meta["version"]

    out = [f"# Final Evaluation Report: {meta['name']}", ""]

    # 1. Summary
    out += ["## 1. Summary", ""]
    if base:
        shared = [m for m in runs if m in base["runs"]]
        out.append(f"Comparison of `{meta['name']}` version {v1} (V1) with version {v2} (V2). "
                   "Charts cover models that ran on both versions.")
        out.append("")
        if shared:
            for title, unit, key in (("Token usage", "tokens", "tokens"), ("Total cost", "USD", "cost"),
                                     ("Time spent", "seconds", "time")):
                out += [chart(title, unit, shared, [base["runs"][m][key] for m in shared],
                              [runs[m][key] for m in shared], key), ""]
        else:
            out += ["_No model ran on both versions, so there is nothing to chart._", ""]
    else:
        out += [f"Evaluation of `{meta['name']}` version {v2} on {len(runs)} model(s): "
                f"{', '.join(runs) or 'none'}.", ""]
    if sim is not None:
        rec = recommend(rec_rows, tolerance)["recommended"]
        out += [f"Recommended model: **{rec['model']}** (see section 8)." if rec
                else "No model could be recommended (see section 8).", ""]

    # 2, 3
    version_line = f"Version: `{v2}`" + (f" (compared with `{v1}`)" if base else "")
    out += ["## 2. Skill name", "", f"Name: `{meta['name']}`  ", version_line, ""]
    out += ["## 3. Skill description", "", meta["description"] or "_No description found._", ""]

    # 4. Run results
    out += ["## 4. Run results", ""]
    if base:
        out += compare_run_table(base["runs"], runs, v1, v2) + [""]
        out += [f"Current version ({v2}):", ""]
    out += run_table(runs) + [""]

    # 5. Output comparison
    out += ["## 5. Output comparison", "", COMPARE_HEADER, "| --- | --- | --- | --- | --- |"]
    out += cmp_rows or ["| _none_ | | | | |"]
    out.append("")
    if sim is not None and sim["cases"]:
        out += ["Similarity per case (details in `step_reports/05_similarity.md`):", "",
                "| Case | Model | Similarity | Fact recall | Content overlap | Structure |",
                "| --- | --- | ---: | ---: | ---: | ---: |"]
        out += ["| " + " | ".join(c) + " |" for c in sim["cases"]]
        out.append("")
    if base:
        old_notes = {(c[0], c[2]): c[4] for c in base["comparison"] if len(c) >= 5}
        out += ["Notes side by side:", "", f"| Verified output | Model | Notes V1 ({v1}) | Notes V2 ({v2}) |",
                "| --- | --- | --- | --- |"]
        for row in cmp_rows:
            c = split_cells(row)
            if len(c) >= 5:
                out.append(f"| {c[0]} | {c[2]} | {old_notes.get((c[0], c[2]), 'n/a')} | {c[4]} |")
        out.append("")

    # 6. Structure check
    out += ["## 6. Skill structure check", ""]
    if base:
        o, n = counts_line(base["structure"]), counts_line(structure)
        if o and n:
            out += ["| Severity | V1 | V2 | Change |", "| --- | ---: | ---: | ---: |"]
            for label, a, b in zip(("Blocker", "Warning", "Info"), o, n):
                out.append(f"| {label} | {a} | {b} | {b - a:+d} |")
            out.append("")
    out += [demote(structure), ""]

    # 7. Rubric review
    out += ["## 7. Skill rubric review", ""]
    if base:
        out += [f"### 7.1 Current version ({v2})", "", demote(rubric, 3), "",
                f"### 7.2 Previous version ({v1})", "", demote(base["rubric"], 1), ""]
    else:
        out += [demote(rubric), ""]

    # 8. Model recommendation
    out += render_recommendation(rec_rows, tolerance, sim, base)

    return "\n".join(out).rstrip() + "\n"


def main():
    args = sys.argv[1:]

    def opt(name):
        if name in args:
            i = args.index(name)
            if i + 1 >= len(args):
                sys.exit(f"Error: {name} needs a value.")
            return args[i + 1]

    if not args or args[0].startswith("--"):
        sys.exit("Usage: python build_final_report.py <skill_dir> [--baseline <older_skill_dir>] [--out <path>]")
    skill_dir = args[0]
    if not (Path(skill_dir) / "SKILL.md").is_file():
        sys.exit(f"Error: no SKILL.md in {skill_dir}")
    report = build(skill_dir, opt("--baseline"))
    out_path = Path(opt("--out") or Path(skill_dir) / "final_report.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
