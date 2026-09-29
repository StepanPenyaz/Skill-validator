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
    evals/<skill>_<version>_outputs/run_on_<model>_report.md
                                                  lines like "- Tokens used: 35120",
                                                  "- Time spent: 5m 12s", "- Total cost: $0.2107"

Writes <skill_dir>/final_report.md unless --out is given. Sections are
numbered from 1.

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
